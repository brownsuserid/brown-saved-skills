"""Calculate shipping costs based on order details and region."""

from typing import Any

# Shipping rate tiers: (max_items, cost_per_item)
DOMESTIC_RATES = [
    (5, 3.00),
    (20, 2.50),
    (50, 2.00),
    (None, 1.50),  # 50+ items
]

INTERNATIONAL_RATES = [
    (5, 8.00),
    (20, 6.50),
    (50, 5.00),
    (None, 4.00),
]


def _get_rate_table(region: str) -> list[tuple[int | None, float]]:
    """Get the shipping rate table for a region."""
    if region == "international":
        return INTERNATIONAL_RATES
    return DOMESTIC_RATES


def calculate_shipping(order: dict[str, Any]) -> dict[str, Any]:
    """Calculate shipping cost for an order using tiered rates.

    Uses a tiered system where items are split across rate brackets.
    For example, 25 items domestic: first 5 at $3, next 15 at $2.50, last 5 at $2.

    Args:
        order: Order dict with 'quantity' and 'shipping_region'.

    Returns:
        Order dict with 'shipping_cost' and 'shipping_breakdown' added.
    """
    quantity = order["quantity"]
    region = order.get("shipping_region", "domestic")
    rates = _get_rate_table(region)

    # Split quantity across rate tiers
    remaining = quantity
    total_cost = 0.0
    breakdown = []

    prev_max = 0
    for max_items, rate in rates:
        if max_items is None:
            tier_qty = remaining
        else:
            tier_capacity = max_items - prev_max
            tier_qty = min(remaining, tier_capacity)

        if tier_qty > 0:
            tier_cost = tier_qty * rate
            total_cost += tier_cost
            # BUG MANIFESTS HERE: when quantity is float (from order_parser),
            # prev_max + 1 and prev_max + tier_qty produce floats like 1.0, 5.0
            # causing tier labels like "1.0-5.0" instead of "1-5"
            breakdown.append(
                {
                    "tier": f"{prev_max + 1}-{prev_max + tier_qty}",
                    "items": tier_qty,
                    "rate": rate,
                    "cost": tier_cost,
                }
            )

        remaining -= tier_qty
        if remaining <= 0:
            break
        if max_items is not None:
            prev_max = max_items

    return {
        **order,
        "shipping_cost": round(total_cost, 2),
        "shipping_breakdown": breakdown,
    }


def calculate_order_total(order: dict[str, Any]) -> dict[str, Any]:
    """Calculate final order total including shipping.

    Args:
        order: Order dict with 'final_total' from pricing.

    Returns:
        Order dict with 'shipping_cost' and 'order_total' added.
    """
    order_with_shipping = calculate_shipping(order)
    order_with_shipping["order_total"] = round(
        order_with_shipping["final_total"] + order_with_shipping["shipping_cost"], 2
    )
    return order_with_shipping
