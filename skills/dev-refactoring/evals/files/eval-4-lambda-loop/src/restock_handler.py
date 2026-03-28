"""Lambda: Handles restock requests from the enrichment step."""

import json
import os

import boto3

dynamodb = boto3.resource("dynamodb")
sns = boto3.client("sns")


def handler(event, context):
    """Process restock requests.

    Triggered by SQS messages from the enricher when items are
    out of stock. Updates inventory, which fires a DynamoDB stream
    that triggers the enricher again — potential infinite loop if
    the restocked quantity is still insufficient.
    """
    inventory_table = dynamodb.Table(os.environ["INVENTORY_TABLE"])

    for record in event.get("Records", []):
        body = json.loads(record["body"])
        order_id = body.get("order_id")
        items_needed = body.get("items_needed", [])

        for item in items_needed:
            sku = item["sku"]
            needed = item.get("quantity", 1)

            # "Restock" by adding a small amount — but this might
            # not be enough, causing the enricher to request
            # another restock when it re-checks
            restock_amount = max(1, needed)

            inventory_table.update_item(
                Key={"sku": sku},
                UpdateExpression=("SET quantity = if_not_exists(quantity, :zero) + :restock"),
                ExpressionAttributeValues={
                    ":restock": restock_amount,
                    ":zero": 0,
                },
            )

            # PROBLEM: Publishes restock event to the same SNS topic,
            # which the enricher also subscribes to — triggering
            # re-enrichment for orders that referenced this SKU
            sns.publish(
                TopicArn=os.environ["ORDER_EVENTS_TOPIC"],
                Message=json.dumps(
                    {
                        "event_type": "item_restocked",
                        "sku": sku,
                        "order_id": order_id,
                        "restocked_quantity": restock_amount,
                    }
                ),
                MessageAttributes={
                    "event_type": {
                        "DataType": "String",
                        "StringValue": "item_restocked",
                    }
                },
            )

    return {"statusCode": 200}
