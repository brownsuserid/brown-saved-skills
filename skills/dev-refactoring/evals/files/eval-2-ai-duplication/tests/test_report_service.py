"""Basic tests for ReportService."""

from unittest.mock import MagicMock

from src.report_service import ReportService


def _make_service():
    return ReportService(db=MagicMock(), formatter=MagicMock())


def _sample_orders():
    return [
        {
            "order_id": "ORD-001",
            "customer": {"name": "Alice", "email": "alice@test.com"},
            "total": 59.99,
            "tax": 4.80,
            "shipping_cost": 5.99,
            "status": "confirmed",
            "created_at": "2025-01-15T10:30:00",
            "items": [{"product_id": "P1", "quantity": 1}],
        },
        {
            "order_id": "ORD-002",
            "customer": {"name": "Bob", "email": "bob@test.com"},
            "total": 120.00,
            "tax": 9.60,
            "shipping_cost": 0,
            "status": "confirmed",
            "created_at": "2025-01-15T14:00:00",
            "items": [{"product_id": "P2", "quantity": 3}],
        },
    ]


def test_get_daily_orders():
    svc = _make_service()
    svc.db.find_many.return_value = _sample_orders()
    result = svc.get_daily_orders("2025-01-15")
    assert len(result) == 2
    assert result[0]["order_id"] == "ORD-001"


def test_get_daily_revenue():
    svc = _make_service()
    svc.db.find_many.return_value = _sample_orders()
    result = svc.get_daily_revenue("2025-01-15")
    assert result["order_count"] == 2
    assert result["total_revenue"] == 179.99
