"""Parse raw order data from CSV imports into structured order dicts."""

from typing import Any


def parse_order_row(row: dict[str, str]) -> dict[str, Any]:
    """Parse a single CSV row into a structured order.

    Args:
        row: Dict with string keys/values from csv.DictReader.

    Returns:
        Structured order dict with typed fields.
    """
    return {
        "order_id": row["order_id"],
        "customer": row["customer"],
        "product": row["product"],
        # BUG: float() instead of int() — quantities should be whole numbers
        # This is the ROOT CAUSE but the error shows up 3 layers away in shipping
        "quantity": float(row["quantity"]),
        "unit_price": float(row["unit_price"]),
        "shipping_region": row.get("region", "domestic"),
    }


def parse_order_batch(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Parse a batch of CSV rows into structured orders.

    Args:
        rows: List of dicts from csv.DictReader.

    Returns:
        List of structured order dicts.
    """
    return [parse_order_row(row) for row in rows]
