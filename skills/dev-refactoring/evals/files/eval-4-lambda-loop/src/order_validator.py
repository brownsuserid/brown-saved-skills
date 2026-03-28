"""Lambda: Validates incoming orders and publishes to SNS for downstream processing."""

import json
import os

import boto3

sns = boto3.client("sns")
sfn = boto3.client("stepfunctions")
dynamodb = boto3.resource("dynamodb")


def handler(event, context):
    """Validate order and fan out to processing pipeline."""
    table = dynamodb.Table(os.environ["ORDERS_TABLE"])

    for record in event.get("Records", []):
        if record.get("eventSource") == "aws:sqs":
            order = json.loads(record["body"])
        elif record.get("source") == "aws.events":
            # EventBridge trigger for retry
            order = record["detail"]
        else:
            order = record

        order_id = order.get("order_id")
        if not order_id:
            print("Missing order_id, skipping")
            continue

        # Check if already processed (idempotency)
        existing = table.get_item(Key={"order_id": order_id}).get("Item")
        if existing and existing.get("status") == "validated":
            print(f"Order {order_id} already validated, skipping")
            continue

        # Validate order fields
        errors = []
        if not order.get("customer_email"):
            errors.append("missing customer_email")
        if not order.get("items") or len(order["items"]) == 0:
            errors.append("missing items")
        for item in order.get("items", []):
            if not item.get("sku"):
                errors.append("item missing sku")
            if not item.get("quantity") or item["quantity"] < 1:
                errors.append(f"invalid quantity for {item.get('sku')}")

        if errors:
            # PROBLEM: On validation failure, publishes to the SAME SNS topic
            # that the enrichment lambda subscribes to, which then calls back
            # to the step function, which retries validation — creating a loop.
            table.put_item(
                Item={
                    "order_id": order_id,
                    "status": "validation_failed",
                    "errors": errors,
                    **order,
                }
            )
            sns.publish(
                TopicArn=os.environ["ORDER_EVENTS_TOPIC"],
                Message=json.dumps(
                    {
                        "event_type": "order_validation_failed",
                        "order_id": order_id,
                        "errors": errors,
                        "order": order,
                    }
                ),
                MessageAttributes={
                    "event_type": {
                        "DataType": "String",
                        "StringValue": "order_validation_failed",
                    }
                },
            )
            continue

        # Valid order — save and start step function
        table.put_item(
            Item={
                "order_id": order_id,
                "status": "validated",
                **order,
            }
        )

        # Start the orchestration pipeline
        sfn.start_execution(
            stateMachineArn=os.environ["PIPELINE_STATE_MACHINE"],
            name=f"order-{order_id}",
            input=json.dumps({"order_id": order_id, **order}),
        )

        # ALSO publishes success to SNS — the enrichment lambda picks
        # this up AND the step function also invokes enrichment directly
        sns.publish(
            TopicArn=os.environ["ORDER_EVENTS_TOPIC"],
            Message=json.dumps(
                {
                    "event_type": "order_validated",
                    "order_id": order_id,
                }
            ),
            MessageAttributes={
                "event_type": {
                    "DataType": "String",
                    "StringValue": "order_validated",
                }
            },
        )
