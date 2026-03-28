"""Order management system - handles everything from validation to fulfillment."""

import re
from datetime import datetime, timedelta
from typing import Any


class OrderManager:
    """Manages the entire order lifecycle."""

    def __init__(
        self,
        db_connection,
        email_service,
        payment_gateway,
        inventory_service,
        shipping_service,
        logger,
    ):
        self.db = db_connection
        self.email = email_service
        self.payment = payment_gateway
        self.inventory = inventory_service
        self.shipping = shipping_service
        self.logger = logger
        self.tax_rates = {"US": 0.08, "CA": 0.13, "UK": 0.20, "DE": 0.19, "AU": 0.10, "JP": 0.10}
        self.discount_rules = {}
        self.order_count = 0

    def process_order(self, order_data: dict[str, Any]) -> dict[str, Any]:
        """Process an incoming order from start to finish."""
        self.order_count += 1

        # Validate customer
        if not order_data.get("customer"):
            return {"status": "error", "message": "Missing customer data"}
        customer = order_data["customer"]
        if not customer.get("email"):
            return {"status": "error", "message": "Missing customer email"}
        if not re.match(r"[^@]+@[^@]+\.[^@]+", customer["email"]):
            return {"status": "error", "message": "Invalid email format"}
        if not customer.get("name"):
            return {"status": "error", "message": "Missing customer name"}
        if not customer.get("address"):
            return {"status": "error", "message": "Missing customer address"}
        if not customer["address"].get("street"):
            return {"status": "error", "message": "Missing street address"}
        if not customer["address"].get("city"):
            return {"status": "error", "message": "Missing city"}
        if not customer["address"].get("country"):
            return {"status": "error", "message": "Missing country"}

        # Validate items
        if not order_data.get("items") or len(order_data["items"]) == 0:
            return {"status": "error", "message": "Order must contain items"}

        for item in order_data["items"]:
            if not item.get("product_id"):
                return {"status": "error", "message": "Item missing product_id"}
            if not item.get("quantity") or item["quantity"] < 1:
                return {
                    "status": "error",
                    "message": f"Invalid quantity for {item.get('product_id', 'unknown')}",
                }
            if not item.get("price") or item["price"] <= 0:
                return {
                    "status": "error",
                    "message": f"Invalid price for {item.get('product_id', 'unknown')}",
                }

        # Check inventory for each item
        for item in order_data["items"]:
            stock = self.inventory.check_stock(item["product_id"])
            if stock < item["quantity"]:
                return {
                    "status": "error",
                    "message": f"Insufficient stock for {item['product_id']}",
                }

        # Calculate totals
        subtotal = 0
        for item in order_data["items"]:
            item_total = item["price"] * item["quantity"]
            # Apply per-item discounts
            if item.get("discount_code"):
                discount = self._lookup_discount(item["discount_code"])
                if discount:
                    if discount["type"] == "percentage":
                        item_total = item_total * (1 - discount["value"] / 100)
                    elif discount["type"] == "fixed":
                        item_total = max(0, item_total - discount["value"])
            subtotal += item_total

        # Apply order-level discount
        if order_data.get("discount_code"):
            discount = self._lookup_discount(order_data["discount_code"])
            if discount:
                if discount["type"] == "percentage":
                    subtotal = subtotal * (1 - discount["value"] / 100)
                elif discount["type"] == "fixed":
                    subtotal = max(0, subtotal - discount["value"])

        # Calculate tax
        country = customer["address"]["country"]
        tax_rate = self.tax_rates.get(country, 0.0)
        tax = subtotal * tax_rate

        # Calculate shipping
        total_weight = 0
        for item in order_data["items"]:
            weight = item.get("weight", 0.5)
            total_weight += weight * item["quantity"]

        if total_weight <= 1:
            shipping_cost = 5.99
        elif total_weight <= 5:
            shipping_cost = 9.99
        elif total_weight <= 10:
            shipping_cost = 14.99
        elif total_weight <= 25:
            shipping_cost = 24.99
        else:
            shipping_cost = 24.99 + (total_weight - 25) * 1.50

        # Free shipping for orders over 100
        if subtotal > 100:
            shipping_cost = 0

        # Express shipping surcharge
        if order_data.get("shipping_method") == "express":
            shipping_cost += 15.00
        elif order_data.get("shipping_method") == "overnight":
            shipping_cost += 35.00

        total = subtotal + tax + shipping_cost

        # Process payment
        try:
            payment_result = self.payment.charge(
                amount=total,
                currency=order_data.get("currency", "USD"),
                customer_email=customer["email"],
                payment_method=order_data.get("payment_method", "credit_card"),
            )
            if not payment_result.get("success"):
                self.logger.error(
                    f"Payment failed for {customer['email']}: {payment_result.get('error')}"
                )
                return {
                    "status": "error",
                    "message": f"Payment failed: {payment_result.get('error', 'Unknown error')}",
                }
        except Exception as e:
            self.logger.error(f"Payment exception for {customer['email']}: {str(e)}")
            return {"status": "error", "message": f"Payment processing error: {str(e)}"}

        # Reserve inventory
        for item in order_data["items"]:
            self.inventory.reserve(item["product_id"], item["quantity"])

        # Create order record
        order_id = f"ORD-{datetime.now().strftime('%Y%m%d')}-{self.order_count:05d}"
        order_record = {
            "order_id": order_id,
            "customer": customer,
            "items": order_data["items"],
            "subtotal": round(subtotal, 2),
            "tax": round(tax, 2),
            "shipping_cost": round(shipping_cost, 2),
            "total": round(total, 2),
            "payment_id": payment_result.get("transaction_id"),
            "status": "confirmed",
            "created_at": datetime.now().isoformat(),
            "shipping_method": order_data.get("shipping_method", "standard"),
        }

        # Save to database
        self.db.insert("orders", order_record)

        # Schedule shipping
        if order_data.get("shipping_method") == "overnight":
            ship_by = datetime.now() + timedelta(hours=4)
        elif order_data.get("shipping_method") == "express":
            ship_by = datetime.now() + timedelta(days=1)
        else:
            ship_by = datetime.now() + timedelta(days=3)

        shipping_request = {
            "order_id": order_id,
            "address": customer["address"],
            "items": order_data["items"],
            "weight": total_weight,
            "method": order_data.get("shipping_method", "standard"),
            "ship_by": ship_by.isoformat(),
        }
        self.shipping.schedule(shipping_request)

        # Send confirmation email
        email_body = f"""
        Dear {customer["name"]},

        Thank you for your order!

        Order ID: {order_id}
        Items: {len(order_data["items"])}
        Subtotal: ${subtotal:.2f}
        Tax: ${tax:.2f}
        Shipping: ${shipping_cost:.2f}
        Total: ${total:.2f}

        Your order will be shipped by {ship_by.strftime("%B %d, %Y")}.

        Thank you for shopping with us!
        """
        self.email.send(
            to=customer["email"],
            subject=f"Order Confirmation - {order_id}",
            body=email_body,
        )

        self.logger.info(f"Order {order_id} processed successfully for {customer['email']}")

        return {
            "status": "success",
            "order_id": order_id,
            "total": round(total, 2),
            "estimated_delivery": ship_by.isoformat(),
        }

    def cancel_order(self, order_id: str, reason: str = "") -> dict[str, Any]:
        """Cancel an existing order."""
        order = self.db.find("orders", {"order_id": order_id})
        if not order:
            return {"status": "error", "message": "Order not found"}

        if order["status"] == "shipped":
            return {"status": "error", "message": "Cannot cancel shipped order"}
        if order["status"] == "delivered":
            return {"status": "error", "message": "Cannot cancel delivered order"}
        if order["status"] == "cancelled":
            return {"status": "error", "message": "Order already cancelled"}

        # Refund payment
        try:
            refund_result = self.payment.refund(order["payment_id"], order["total"])
            if not refund_result.get("success"):
                return {
                    "status": "error",
                    "message": f"Refund failed: {refund_result.get('error')}",
                }
        except Exception as e:
            self.logger.error(f"Refund exception for {order_id}: {str(e)}")
            return {"status": "error", "message": f"Refund processing error: {str(e)}"}

        # Release inventory
        for item in order["items"]:
            self.inventory.release(item["product_id"], item["quantity"])

        # Cancel shipping
        self.shipping.cancel(order_id)

        # Update order status
        self.db.update(
            "orders",
            {"order_id": order_id},
            {
                "status": "cancelled",
                "cancelled_at": datetime.now().isoformat(),
                "cancel_reason": reason,
            },
        )

        # Send cancellation email
        self.email.send(
            to=order["customer"]["email"],
            subject=f"Order Cancelled - {order_id}",
            body=(
                f"Dear {order['customer']['name']},\n\n"
                f"Your order {order_id} has been cancelled.\n"
                f"Reason: {reason or 'Customer request'}\n\n"
                f"A refund of ${order['total']:.2f} will be processed "
                f"within 3-5 business days.\n\nThank you."
            ),
        )

        self.logger.info(f"Order {order_id} cancelled. Reason: {reason}")
        return {"status": "success", "message": "Order cancelled", "refund_amount": order["total"]}

    def get_order_status(self, order_id: str) -> dict[str, Any]:
        """Get current status of an order."""
        order = self.db.find("orders", {"order_id": order_id})
        if not order:
            return {"status": "error", "message": "Order not found"}

        tracking = self.shipping.get_tracking(order_id)

        return {
            "order_id": order_id,
            "status": order["status"],
            "total": order["total"],
            "created_at": order["created_at"],
            "tracking": tracking,
        }

    def generate_report(self, start_date: str, end_date: str) -> dict[str, Any]:
        """Generate sales report for date range."""
        orders = self.db.find_many("orders", {"created_at": {"$gte": start_date, "$lte": end_date}})

        total_revenue = 0
        total_tax = 0
        total_shipping = 0
        items_sold = 0
        orders_by_status = {}
        orders_by_country = {}
        daily_revenue = {}

        for order in orders:
            total_revenue += order["total"]
            total_tax += order["tax"]
            total_shipping += order["shipping_cost"]

            for item in order["items"]:
                items_sold += item["quantity"]

            status = order["status"]
            if status not in orders_by_status:
                orders_by_status[status] = 0
            orders_by_status[status] += 1

            country = order["customer"]["address"]["country"]
            if country not in orders_by_country:
                orders_by_country[country] = {"count": 0, "revenue": 0}
            orders_by_country[country]["count"] += 1
            orders_by_country[country]["revenue"] += order["total"]

            date_key = order["created_at"][:10]
            if date_key not in daily_revenue:
                daily_revenue[date_key] = 0
            daily_revenue[date_key] += order["total"]

        return {
            "period": {"start": start_date, "end": end_date},
            "total_orders": len(orders),
            "total_revenue": round(total_revenue, 2),
            "total_tax": round(total_tax, 2),
            "total_shipping": round(total_shipping, 2),
            "items_sold": items_sold,
            "average_order_value": round(total_revenue / len(orders), 2) if orders else 0,
            "orders_by_status": orders_by_status,
            "orders_by_country": orders_by_country,
            "daily_revenue": daily_revenue,
        }

    def _lookup_discount(self, code: str) -> dict | None:
        """Look up a discount code."""
        if code in self.discount_rules:
            discount = self.discount_rules[code]
            if discount.get("expires_at"):
                if datetime.fromisoformat(discount["expires_at"]) < datetime.now():
                    return None
            if discount.get("max_uses") and discount.get("used", 0) >= discount["max_uses"]:
                return None
            return discount
        return None
