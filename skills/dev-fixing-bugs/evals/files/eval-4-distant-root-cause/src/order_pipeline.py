"""End-to-end order processing pipeline."""

from typing import Any

from src.order_parser import parse_order_batch
from src.pricing import apply_bulk_discount
from src.report import generate_order_report
from src.shipping import calculate_order_total


def process_orders(raw_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Process raw CSV order rows through the full pipeline.

    Pipeline: parse -> price -> ship -> total

    Args:
        raw_rows: List of dicts from csv.DictReader.

    Returns:
        List of fully processed order dicts.
    """
    orders = parse_order_batch(raw_rows)
    priced = [apply_bulk_discount(order) for order in orders]
    completed = [calculate_order_total(order) for order in priced]
    return completed


def process_and_report(raw_rows: list[dict[str, str]]) -> dict[str, Any]:
    """Process orders and generate a validated report.

    Args:
        raw_rows: List of dicts from csv.DictReader.

    Returns:
        Report dict with summary statistics.

    Raises:
        ValueError: If shipping tier labels are malformed.
    """
    completed = process_orders(raw_rows)
    return generate_order_report(completed)
