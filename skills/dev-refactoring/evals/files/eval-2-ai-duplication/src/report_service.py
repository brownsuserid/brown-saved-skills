"""Report generation service with AI-generated duplication patterns."""

from datetime import datetime, timedelta
from typing import Any


class ReportService:
    """Generates various reports from order data."""

    def __init__(self, db, formatter):
        self.db = db
        self.formatter = formatter

    def get_daily_orders(self, date: str) -> list[dict[str, Any]]:
        """Get all orders for a specific date."""
        start = f"{date}T00:00:00"
        end = f"{date}T23:59:59"
        orders = self.db.find_many("orders", {"created_at": {"$gte": start, "$lte": end}})
        results = []
        for order in orders:
            results.append(
                {
                    "order_id": order["order_id"],
                    "customer_name": order["customer"]["name"],
                    "total": order["total"],
                    "status": order["status"],
                    "created_at": order["created_at"],
                }
            )
        return results

    def get_weekly_orders(self, start_date: str) -> list[dict[str, Any]]:
        """Get all orders for a week starting from start_date."""
        start = f"{start_date}T00:00:00"
        end_dt = datetime.fromisoformat(start_date) + timedelta(days=7)
        end = f"{end_dt.strftime('%Y-%m-%d')}T23:59:59"
        orders = self.db.find_many("orders", {"created_at": {"$gte": start, "$lte": end}})
        results = []
        for order in orders:
            results.append(
                {
                    "order_id": order["order_id"],
                    "customer_name": order["customer"]["name"],
                    "total": order["total"],
                    "status": order["status"],
                    "created_at": order["created_at"],
                }
            )
        return results

    def get_monthly_orders(self, year: int, month: int) -> list[dict[str, Any]]:
        """Get all orders for a specific month."""
        start = f"{year}-{month:02d}-01T00:00:00"
        if month == 12:
            end = f"{year + 1}-01-01T00:00:00"
        else:
            end = f"{year}-{month + 1:02d}-01T00:00:00"
        orders = self.db.find_many("orders", {"created_at": {"$gte": start, "$lt": end}})
        results = []
        for order in orders:
            results.append(
                {
                    "order_id": order["order_id"],
                    "customer_name": order["customer"]["name"],
                    "total": order["total"],
                    "status": order["status"],
                    "created_at": order["created_at"],
                }
            )
        return results

    def get_daily_revenue(self, date: str) -> dict[str, Any]:
        """Calculate revenue for a specific date."""
        start = f"{date}T00:00:00"
        end = f"{date}T23:59:59"
        orders = self.db.find_many("orders", {"created_at": {"$gte": start, "$lte": end}})
        total_revenue = 0
        total_tax = 0
        total_shipping = 0
        order_count = 0
        for order in orders:
            if order["status"] != "cancelled":
                total_revenue += order["total"]
                total_tax += order["tax"]
                total_shipping += order["shipping_cost"]
                order_count += 1
        return {
            "date": date,
            "total_revenue": round(total_revenue, 2),
            "total_tax": round(total_tax, 2),
            "total_shipping": round(total_shipping, 2),
            "order_count": order_count,
            "average_order_value": (
                round(total_revenue / order_count, 2) if order_count > 0 else 0
            ),
        }

    def get_weekly_revenue(self, start_date: str) -> dict[str, Any]:
        """Calculate revenue for a week starting from start_date."""
        start = f"{start_date}T00:00:00"
        end_dt = datetime.fromisoformat(start_date) + timedelta(days=7)
        end = f"{end_dt.strftime('%Y-%m-%d')}T23:59:59"
        orders = self.db.find_many("orders", {"created_at": {"$gte": start, "$lte": end}})
        total_revenue = 0
        total_tax = 0
        total_shipping = 0
        order_count = 0
        for order in orders:
            if order["status"] != "cancelled":
                total_revenue += order["total"]
                total_tax += order["tax"]
                total_shipping += order["shipping_cost"]
                order_count += 1
        return {
            "period": f"{start_date} to {end_dt.strftime('%Y-%m-%d')}",
            "total_revenue": round(total_revenue, 2),
            "total_tax": round(total_tax, 2),
            "total_shipping": round(total_shipping, 2),
            "order_count": order_count,
            "average_order_value": (
                round(total_revenue / order_count, 2) if order_count > 0 else 0
            ),
        }

    def get_monthly_revenue(self, year: int, month: int) -> dict[str, Any]:
        """Calculate revenue for a specific month."""
        start = f"{year}-{month:02d}-01T00:00:00"
        if month == 12:
            end = f"{year + 1}-01-01T00:00:00"
        else:
            end = f"{year}-{month + 1:02d}-01T00:00:00"
        orders = self.db.find_many("orders", {"created_at": {"$gte": start, "$lt": end}})
        total_revenue = 0
        total_tax = 0
        total_shipping = 0
        order_count = 0
        for order in orders:
            if order["status"] != "cancelled":
                total_revenue += order["total"]
                total_tax += order["tax"]
                total_shipping += order["shipping_cost"]
                order_count += 1
        return {
            "period": f"{year}-{month:02d}",
            "total_revenue": round(total_revenue, 2),
            "total_tax": round(total_tax, 2),
            "total_shipping": round(total_shipping, 2),
            "order_count": order_count,
            "average_order_value": (
                round(total_revenue / order_count, 2) if order_count > 0 else 0
            ),
        }

    def get_active_customers(self) -> list[dict[str, Any]]:
        """Get customers with active orders."""
        orders = self.db.find_many("orders", {"status": "confirmed"})
        customers = {}
        for order in orders:
            email = order["customer"]["email"]
            if email not in customers:
                customers[email] = {
                    "email": email,
                    "name": order["customer"]["name"],
                    "order_count": 0,
                    "total_spent": 0,
                }
            customers[email]["order_count"] += 1
            customers[email]["total_spent"] += order["total"]
        return list(customers.values())

    def get_inactive_customers(self, days_inactive: int = 90) -> list[dict[str, Any]]:
        """Get customers with no orders in the last N days."""
        cutoff = (datetime.now() - timedelta(days=days_inactive)).isoformat()
        all_orders = self.db.find_many("orders", {})
        customers = {}
        for order in all_orders:
            email = order["customer"]["email"]
            if email not in customers:
                customers[email] = {
                    "email": email,
                    "name": order["customer"]["name"],
                    "order_count": 0,
                    "total_spent": 0,
                    "last_order": order["created_at"],
                }
            customers[email]["order_count"] += 1
            customers[email]["total_spent"] += order["total"]
            if order["created_at"] > customers[email]["last_order"]:
                customers[email]["last_order"] = order["created_at"]
        return [c for c in customers.values() if c["last_order"] < cutoff]

    def get_vip_customers(
        self,
        min_spent: float = 1000,
    ) -> list[dict[str, Any]]:
        """Get customers who have spent more than min_spent."""
        all_orders = self.db.find_many("orders", {})
        customers = {}
        for order in all_orders:
            email = order["customer"]["email"]
            if email not in customers:
                customers[email] = {
                    "email": email,
                    "name": order["customer"]["name"],
                    "order_count": 0,
                    "total_spent": 0,
                }
            customers[email]["order_count"] += 1
            customers[email]["total_spent"] += order["total"]
        return [c for c in customers.values() if c["total_spent"] >= min_spent]

    def format_daily_report(self, date: str) -> str:
        """Format a daily report as text."""
        orders = self.get_daily_orders(date)
        revenue = self.get_daily_revenue(date)
        lines = [f"Daily Report - {date}", "=" * 40]
        lines.append(f"Orders: {revenue['order_count']}")
        lines.append(f"Revenue: ${revenue['total_revenue']:.2f}")
        lines.append(f"Tax: ${revenue['total_tax']:.2f}")
        lines.append(f"Shipping: ${revenue['total_shipping']:.2f}")
        lines.append(f"Avg Order: ${revenue['average_order_value']:.2f}")
        lines.append("")
        lines.append("Order Details:")
        for order in orders:
            lines.append(
                f"  {order['order_id']} - {order['customer_name']}"
                f" - ${order['total']:.2f} ({order['status']})"
            )
        return "\n".join(lines)

    def format_weekly_report(self, start_date: str) -> str:
        """Format a weekly report as text."""
        orders = self.get_weekly_orders(start_date)
        revenue = self.get_weekly_revenue(start_date)
        lines = [
            f"Weekly Report - Week of {start_date}",
            "=" * 40,
        ]
        lines.append(f"Orders: {revenue['order_count']}")
        lines.append(f"Revenue: ${revenue['total_revenue']:.2f}")
        lines.append(f"Tax: ${revenue['total_tax']:.2f}")
        lines.append(f"Shipping: ${revenue['total_shipping']:.2f}")
        lines.append(f"Avg Order: ${revenue['average_order_value']:.2f}")
        lines.append("")
        lines.append("Order Details:")
        for order in orders:
            lines.append(
                f"  {order['order_id']} - {order['customer_name']}"
                f" - ${order['total']:.2f} ({order['status']})"
            )
        return "\n".join(lines)

    def format_monthly_report(self, year: int, month: int) -> str:
        """Format a monthly report as text."""
        orders = self.get_monthly_orders(year, month)
        revenue = self.get_monthly_revenue(year, month)
        lines = [
            f"Monthly Report - {year}-{month:02d}",
            "=" * 40,
        ]
        lines.append(f"Orders: {revenue['order_count']}")
        lines.append(f"Revenue: ${revenue['total_revenue']:.2f}")
        lines.append(f"Tax: ${revenue['total_tax']:.2f}")
        lines.append(f"Shipping: ${revenue['total_shipping']:.2f}")
        lines.append(f"Avg Order: ${revenue['average_order_value']:.2f}")
        lines.append("")
        lines.append("Order Details:")
        for order in orders:
            lines.append(
                f"  {order['order_id']} - {order['customer_name']}"
                f" - ${order['total']:.2f} ({order['status']})"
            )
        return "\n".join(lines)
