"""Shopping cart with discount and coupon logic."""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional


@dataclass
class CartItem:
    name: str
    price: Decimal
    quantity: int = 1

    @property
    def subtotal(self) -> Decimal:
        return self.price * self.quantity


@dataclass
class Coupon:
    code: str
    discount_type: str  # "percentage" or "fixed"
    value: Decimal
    min_purchase: Decimal = Decimal("0")
    max_uses: int = 1
    uses: int = 0

    @property
    def is_valid(self) -> bool:
        return self.uses < self.max_uses


class ShoppingCart:
    """Shopping cart with support for items, quantities, coupons, and bulk discounts."""

    BULK_DISCOUNT_THRESHOLD = 10
    BULK_DISCOUNT_RATE = Decimal("0.05")  # 5% off for 10+ of same item
    MAX_ITEMS_PER_PRODUCT = 99
    MAX_CART_TOTAL = Decimal("99999.99")

    def __init__(self):
        self._items: dict[str, CartItem] = {}
        self._coupon: Optional[Coupon] = None

    def add_item(self, name: str, price: Decimal, quantity: int = 1) -> None:
        """Add an item to the cart.

        Raises:
            ValueError: If price is negative, quantity < 1, or would exceed max.
        """
        if price < 0:
            raise ValueError(f"Price cannot be negative: {price}")
        if quantity < 1:
            raise ValueError(f"Quantity must be at least 1, got {quantity}")

        if name in self._items:
            new_qty = self._items[name].quantity + quantity
            if new_qty > self.MAX_ITEMS_PER_PRODUCT:
                raise ValueError(f"Cannot exceed {self.MAX_ITEMS_PER_PRODUCT} of {name}")
            self._items[name].quantity = new_qty
        else:
            if quantity > self.MAX_ITEMS_PER_PRODUCT:
                raise ValueError(f"Cannot exceed {self.MAX_ITEMS_PER_PRODUCT} of {name}")
            self._items[name] = CartItem(name=name, price=price, quantity=quantity)

    def remove_item(self, name: str, quantity: Optional[int] = None) -> None:
        """Remove item(s) from the cart.

        If quantity is None, removes all of that item.

        Raises:
            KeyError: If item not in cart.
            ValueError: If quantity exceeds what's in cart.
        """
        if name not in self._items:
            raise KeyError(f"Item not in cart: {name}")

        if quantity is None:
            del self._items[name]
        else:
            item = self._items[name]
            if quantity > item.quantity:
                raise ValueError(
                    f"Cannot remove {quantity} of {name}, only {item.quantity} in cart"
                )
            item.quantity -= quantity
            if item.quantity == 0:
                del self._items[name]

    def apply_coupon(self, coupon: Coupon) -> Decimal:
        """Apply a coupon to the cart.

        Returns the discount amount.

        Raises:
            ValueError: If coupon is invalid or minimum purchase not met.
        """
        if not coupon.is_valid:
            raise ValueError(f"Coupon {coupon.code} has been fully used")

        subtotal = self.subtotal
        if subtotal < coupon.min_purchase:
            raise ValueError(
                f"Minimum purchase of {coupon.min_purchase} not met (cart total: {subtotal})"
            )

        self._coupon = coupon
        coupon.uses += 1

        return self._calculate_coupon_discount()

    def _calculate_coupon_discount(self) -> Decimal:
        if not self._coupon:
            return Decimal("0")

        subtotal = self.subtotal
        if self._coupon.discount_type == "percentage":
            discount = subtotal * (self._coupon.value / 100)
        elif self._coupon.discount_type == "fixed":
            discount = min(self._coupon.value, subtotal)
        else:
            discount = Decimal("0")

        return discount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def _calculate_bulk_discounts(self) -> Decimal:
        """Calculate bulk discounts for items with quantity >= threshold."""
        total_discount = Decimal("0")
        for item in self._items.values():
            if item.quantity >= self.BULK_DISCOUNT_THRESHOLD:
                total_discount += item.subtotal * self.BULK_DISCOUNT_RATE
        return total_discount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @property
    def subtotal(self) -> Decimal:
        """Sum of all item subtotals before discounts."""
        return sum(
            (item.subtotal for item in self._items.values()),
            start=Decimal("0"),
        )

    @property
    def total(self) -> Decimal:
        """Final total after all discounts."""
        raw = self.subtotal - self._calculate_bulk_discounts() - self._calculate_coupon_discount()
        result = max(raw, Decimal("0")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if result > self.MAX_CART_TOTAL:
            raise ValueError(f"Cart total {result} exceeds maximum {self.MAX_CART_TOTAL}")
        return result

    @property
    def item_count(self) -> int:
        """Total number of items (sum of quantities)."""
        return sum(item.quantity for item in self._items.values())

    @property
    def is_empty(self) -> bool:
        return len(self._items) == 0

    def clear(self) -> None:
        """Remove all items and coupon."""
        self._items.clear()
        self._coupon = None
