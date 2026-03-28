"""Basic tests for individual lambda handlers — no loop detection."""

import json
from unittest.mock import MagicMock, patch


def test_validator_skips_missing_order_id():
    """Validator should skip records without order_id."""
    with patch.dict(
        "os.environ",
        {
            "ORDERS_TABLE": "test-orders",
            "ORDER_EVENTS_TOPIC": "arn:aws:sns:us-east-1:123:topic",
            "PIPELINE_STATE_MACHINE": "arn:aws:states:us-east-1:123:sm",
        },
    ):
        with patch("src.order_validator.boto3") as mock_boto:
            mock_table = MagicMock()
            mock_boto.resource.return_value.Table.return_value = mock_table
            from src.order_validator import handler

            handler({"Records": [{"body": json.dumps({})}]}, None)
            mock_table.put_item.assert_not_called()


def test_payment_calculates_total():
    """Payment processor should sum enriched item prices."""
    with patch.dict(
        "os.environ",
        {
            "ORDERS_TABLE": "test-orders",
            "ORDER_EVENTS_TOPIC": "arn:aws:sns:us-east-1:123:topic",
        },
    ):
        with patch("src.payment_processor.boto3") as mock_boto:
            mock_table = MagicMock()
            mock_boto.resource.return_value.Table.return_value = mock_table
            mock_table.get_item.return_value = {
                "Item": {
                    "order_id": "ORD-1",
                    "enriched_items": [
                        {
                            "sku": "A",
                            "current_price": 10,
                            "quantity": 2,
                        },
                        {
                            "sku": "B",
                            "current_price": 25,
                            "quantity": 1,
                        },
                    ],
                }
            }
            from src.payment_processor import handler

            result = handler({"order_id": "ORD-1"}, None)
            assert result["amount"] == 45
