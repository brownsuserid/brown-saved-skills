"""Generate order reports with validation."""

import re
from typing import Any


def validate_shipping_breakdown(breakdown: list[dict[str, Any]]) -> None:
    """Validate that shipping breakdown tiers have correct format.

    Tier labels must be "N-M" where N and M are integers (e.g., "1-5", "6-20").
    This is required by downstream invoice systems that parse tier labels.

    Args:
        breakdown: List of tier dicts from calculate_shipping.

    Raises:
        ValueError: If any tier label doesn't match the expected format.
    """
    pattern = re.compile(r"^\d+-\d+$")
    for tier in breakdown:
        label = tier["tier"]
        if not pattern.match(label):
            raise ValueError(
                f"Invalid shipping tier label '{label}': "
                f"expected format 'N-M' with integers (e.g., '1-5')"
            )


def generate_order_report(orders: list[dict[str, Any]]) -> dict[str, Any]:
    """Generate a summary report for processed orders.

    Validates all shipping breakdowns before generating the report.

    Args:
        orders: List of fully processed order dicts.

    Returns:
        Report dict with summary statistics.
    """
    # Validate all shipping breakdowns
    for order in orders:
        validate_shipping_breakdown(order["shipping_breakdown"])

    total_revenue = sum(o["final_total"] for o in orders)
    total_shipping = sum(o["shipping_cost"] for o in orders)
    total_items = sum(o["quantity"] for o in orders)

    return {
        "order_count": len(orders),
        "total_items": total_items,
        "total_revenue": round(total_revenue, 2),
        "total_shipping": round(total_shipping, 2),
        "grand_total": round(total_revenue + total_shipping, 2),
    }
