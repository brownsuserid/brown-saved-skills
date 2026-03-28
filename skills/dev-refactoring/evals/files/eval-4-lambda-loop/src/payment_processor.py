"""Lambda: Processes payment for enriched orders."""

import json
import os

import boto3

sns = boto3.client("sns")
dynamodb = boto3.resource("dynamodb")
sfn = boto3.client("stepfunctions")


def handler(event, context):
    """Process payment for an order.

    Invoked by Step Function after enrichment.
    On failure, publishes to SNS which triggers the validator
    to re-validate (thinking it's a new order), starting the
    whole pipeline over.
    """
    table = dynamodb.Table(os.environ["ORDERS_TABLE"])
    order_id = event.get("order_id")

    if not order_id:
        raise ValueError("Missing order_id")

    order = table.get_item(Key={"order_id": order_id}).get("Item")
    if not order:
        raise ValueError(f"Order {order_id} not found")

    # Calculate total from enriched items
    total = 0
    for item in order.get("enriched_items", order.get("items", [])):
        price = item.get("current_price", item.get("price", 0))
        qty = item.get("quantity", 1)
        total += price * qty

    # Simulate payment processing
    payment_result = {
        "order_id": order_id,
        "amount": total,
        "currency": "USD",
        "status": "succeeded",
        "transaction_id": f"txn_{order_id}",
    }

    table.update_item(
        Key={"order_id": order_id},
        UpdateExpression=("SET #s = :status, payment = :payment"),
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={
            ":status": "paid",
            ":payment": payment_result,
        },
    )

    # PROBLEM: On payment failure, this publishes to the same SNS
    # topic with event_type "payment_failed". The validator lambda
    # subscribes to this topic without filtering and treats
    # "payment_failed" events as new orders to reprocess — because
    # it re-reads the order from DynamoDB (where status is still
    # "enriched", not "validated") and re-starts the Step Function.
    if payment_result["status"] != "succeeded":
        sns.publish(
            TopicArn=os.environ["ORDER_EVENTS_TOPIC"],
            Message=json.dumps(
                {
                    "event_type": "payment_failed",
                    "order_id": order_id,
                    "error": payment_result.get("error", "unknown"),
                    # Including the full order data means the
                    # validator treats this as a fresh order
                    **order,
                }
            ),
            MessageAttributes={
                "event_type": {
                    "DataType": "String",
                    "StringValue": "payment_failed",
                }
            },
        )
        raise Exception(f"Payment failed for {order_id}: {payment_result.get('error')}")

    # Publish success
    sns.publish(
        TopicArn=os.environ["ORDER_EVENTS_TOPIC"],
        Message=json.dumps(
            {
                "event_type": "payment_succeeded",
                "order_id": order_id,
                "transaction_id": payment_result["transaction_id"],
            }
        ),
        MessageAttributes={
            "event_type": {
                "DataType": "String",
                "StringValue": "payment_succeeded",
            }
        },
    )

    return {
        "order_id": order_id,
        "payment_status": "succeeded",
        "transaction_id": payment_result["transaction_id"],
        "amount": total,
    }
