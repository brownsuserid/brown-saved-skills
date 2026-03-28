"""Tests for order processing pipeline.

NOTE: The unit tests for individual modules pass fine. The bug only surfaces
when running the full pipeline through process_and_report(), which validates
shipping tier labels. The tier labels come out as "1.0-3.0" instead of "1-3".
"""

from src.order_parser import parse_order_batch, parse_order_row
from src.order_pipeline import process_and_report, process_orders
from src.pricing import apply_bulk_discount, calculate_line_total
from src.shipping import calculate_shipping


def make_row(
    order_id: str = "ORD-001",
    customer: str = "Acme Corp",
    product: str = "Widget",
    quantity: str = "5",
    unit_price: str = "10.00",
    region: str = "domestic",
) -> dict[str, str]:
    """Create a CSV-like row dict."""
    return {
        "order_id": order_id,
        "customer": customer,
        "product": product,
        "quantity": quantity,
        "unit_price": unit_price,
        "region": region,
    }


class TestOrderParser:
    def test_parse_basic_row(self):
        row = make_row()
        order = parse_order_row(row)
        assert order["order_id"] == "ORD-001"
        assert order["customer"] == "Acme Corp"
        assert order["quantity"] == 5.0
        assert order["unit_price"] == 10.0

    def test_parse_batch(self):
        rows = [make_row(order_id="ORD-001"), make_row(order_id="ORD-002")]
        orders = parse_order_batch(rows)
        assert len(orders) == 2


class TestPricing:
    def test_line_total(self):
        order = parse_order_row(make_row(quantity="5", unit_price="10.00"))
        assert calculate_line_total(order) == 50.0

    def test_no_discount(self):
        order = parse_order_row(make_row(quantity="5"))
        priced = apply_bulk_discount(order)
        assert priced["discount_pct"] == 0.0
        assert priced["final_total"] == 50.0

    def test_bulk_discount_10(self):
        order = parse_order_row(make_row(quantity="10"))
        priced = apply_bulk_discount(order)
        assert priced["discount_pct"] == 0.05


class TestShipping:
    def test_small_order_domestic(self):
        order = parse_order_row(make_row(quantity="3"))
        order = apply_bulk_discount(order)
        result = calculate_shipping(order)
        assert result["shipping_cost"] == 9.0


class TestFullPipeline:
    def test_process_orders_basic(self):
        rows = [make_row(quantity="3", unit_price="10.00")]
        results = process_orders(rows)
        assert len(results) == 1
        assert results[0]["final_total"] == 30.0

    def test_process_and_report(self):
        """This test FAILS because shipping tier labels are '1.0-3.0'
        instead of '1-3'.

        The error message points to report.py (validation) and the tier
        labels are formatted in shipping.py, but the actual root cause
        is in order_parser.py which converts quantity to float instead
        of int.
        """
        rows = [make_row(quantity="3", unit_price="10.00")]
        report = process_and_report(rows)
        assert report["order_count"] == 1
        assert report["total_revenue"] == 30.0
