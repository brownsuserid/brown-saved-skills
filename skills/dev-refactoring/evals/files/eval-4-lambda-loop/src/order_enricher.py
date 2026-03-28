"""Lambda: Enriches validated orders with inventory and pricing data."""

import json
import os

import boto3

sns = boto3.client("sns")
sfn = boto3.client("stepfunctions")
dynamodb = boto3.resource("dynamodb")
sqs = boto3.client("sqs")


def handler(event, context):
    """Enrich order with inventory checks and current pricing.

    This lambda is invoked by:
    1. The Step Function pipeline (direct invocation)
    2. SNS subscription on ORDER_EVENTS_TOPIC (event-driven)
    3. SQS dead letter reprocessing

    The multiple trigger paths are where the trouble starts.
    """
    table = dynamodb.Table(os.environ["ORDERS_TABLE"])
    inventory_table = dynamodb.Table(os.environ["INVENTORY_TABLE"])

    # Normalize input from different trigger sources
    if "Records" in event:
        # SNS via SQS subscription
        for record in event["Records"]:
            body = json.loads(record["body"])
            if "Message" in body:
                message = json.loads(body["Message"])
            else:
                message = body
            _process_enrichment(message, table, inventory_table)
    elif "order_id" in event:
        # Direct Step Function invocation
        _process_enrichment(event, table, inventory_table)
    elif "detail" in event:
        # EventBridge
        _process_enrichment(event["detail"], table, inventory_table)


def _process_enrichment(message, table, inventory_table):
    """Process a single enrichment request."""
    order_id = message.get("order_id")

    if not order_id:
        print("No order_id in message")
        return

    order = table.get_item(Key={"order_id": order_id}).get("Item")
    if not order:
        print(f"Order {order_id} not found")
        return

    # Skip if already enriched
    if order.get("status") == "enriched":
        print(f"Order {order_id} already enriched")
        # BUG: Even though we skip processing, we still publish
        # an "enrichment_complete" event below due to fall-through
        pass

    # Check inventory for each item
    enriched_items = []
    all_in_stock = True
    for item in order.get("items", []):
        inv = inventory_table.get_item(Key={"sku": item["sku"]}).get("Item", {})
        available = inv.get("quantity", 0)
        enriched_item = {
            **item,
            "current_price": inv.get("price", item.get("price", 0)),
            "in_stock": available >= item.get("quantity", 1),
            "available_quantity": available,
        }
        enriched_items.append(enriched_item)
        if not enriched_item["in_stock"]:
            all_in_stock = False

    # Update order with enriched data
    table.update_item(
        Key={"order_id": order_id},
        UpdateExpression=("SET #s = :status, enriched_items = :items, all_in_stock = :stock"),
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={
            ":status": "enriched",
            ":items": enriched_items,
            ":stock": all_in_stock,
        },
    )

    if not all_in_stock:
        # PROBLEM: Out-of-stock items get sent to a "restock" queue,
        # which triggers a restock lambda, which updates inventory,
        # which triggers a DynamoDB stream, which triggers THIS lambda
        # again to re-enrich — potentially infinite if stock is never
        # sufficient.
        sqs.send_message(
            QueueUrl=os.environ["RESTOCK_QUEUE_URL"],
            MessageBody=json.dumps(
                {
                    "order_id": order_id,
                    "items_needed": [i for i in enriched_items if not i["in_stock"]],
                }
            ),
        )

    # PROBLEM: This publishes regardless of whether we actually did
    # enrichment (the skip case above falls through to here)
    sns.publish(
        TopicArn=os.environ["ORDER_EVENTS_TOPIC"],
        Message=json.dumps(
            {
                "event_type": "enrichment_complete",
                "order_id": order_id,
                "all_in_stock": all_in_stock,
            }
        ),
        MessageAttributes={
            "event_type": {
                "DataType": "String",
                "StringValue": "enrichment_complete",
            }
        },
    )

    # Return for Step Function
    return {
        "order_id": order_id,
        "all_in_stock": all_in_stock,
        "enriched_items": enriched_items,
    }
