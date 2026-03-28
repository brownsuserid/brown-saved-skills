"""Tests for shopping cart — only happy path, needs edge case coverage."""

from decimal import Decimal

from src.shopping_cart import ShoppingCart


def test_add_item():
    cart = ShoppingCart()
    cart.add_item("Widget", Decimal("10.00"))
    assert cart.item_count == 1


def test_total():
    cart = ShoppingCart()
    cart.add_item("Widget", Decimal("10.00"), quantity=2)
    assert cart.total == Decimal("20.00")
