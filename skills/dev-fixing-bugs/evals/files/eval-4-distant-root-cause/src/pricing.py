"""Calculate order totals and apply discount tiers."""

from typing import Any


def calculate_line_total(order: dict[str, Any]) -> float:
    """Calculate the line total for an order.

    Args:
        order: Structured order dict with 'quantity' and 'unit_price'.

    Returns:
        Total price as float.
    """
    return order["quantity"] * order["unit_price"]


def apply_bulk_discount(order: dict[str, Any]) -> dict[str, Any]:
    """Apply bulk discount based on quantity.

    Discount tiers:
        - 10+ items: 5% off
        - 50+ items: 10% off
        - 100+ items: 15% off

    Args:
        order: Structured order dict.

    Returns:
        Order dict with 'line_total', 'discount_pct', and 'final_total' added.
    """
    line_total = calculate_line_total(order)
    quantity = order["quantity"]

    if quantity >= 100:
        discount = 0.15
    elif quantity >= 50:
        discount = 0.10
    elif quantity >= 10:
        discount = 0.05
    else:
        discount = 0.0

    return {
        **order,
        "line_total": line_total,
        "discount_pct": discount,
        "final_total": line_total * (1 - discount),
    }
