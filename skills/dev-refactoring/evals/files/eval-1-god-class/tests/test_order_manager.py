"""Basic tests for OrderManager - intentionally minimal coverage."""

from unittest.mock import MagicMock

from src.order_manager import OrderManager


def _make_manager():
    return OrderManager(
        db_connection=MagicMock(),
        email_service=MagicMock(),
        payment_gateway=MagicMock(),
        inventory_service=MagicMock(),
        shipping_service=MagicMock(),
        logger=MagicMock(),
    )


def _valid_order():
    return {
        "customer": {
            "email": "test@example.com",
            "name": "Test User",
            "address": {
                "street": "123 Main St",
                "city": "Springfield",
                "country": "US",
            },
        },
        "items": [
            {"product_id": "PROD-1", "quantity": 2, "price": 29.99},
        ],
    }


def test_process_order_missing_customer():
    mgr = _make_manager()
    result = mgr.process_order({})
    assert result["status"] == "error"
    assert "customer" in result["message"].lower()


def test_process_order_missing_items():
    mgr = _make_manager()
    order = _valid_order()
    order["items"] = []
    result = mgr.process_order(order)
    assert result["status"] == "error"


def test_process_order_success():
    mgr = _make_manager()
    mgr.inventory.check_stock.return_value = 100
    mgr.payment.charge.return_value = {
        "success": True,
        "transaction_id": "TXN-123",
    }
    result = mgr.process_order(_valid_order())
    assert result["status"] == "success"
    assert "order_id" in result
