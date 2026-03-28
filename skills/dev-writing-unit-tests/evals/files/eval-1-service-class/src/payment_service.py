"""Payment processing service with multiple external dependencies."""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

from app.models import Invoice, Payment, User
from app.notifications import EmailService
from app.providers.stripe_client import StripeClient
from app.providers.tax_calculator import TaxCalculator


class PaymentService:
    """Handles payment processing, refunds, and invoice generation."""

    def __init__(
        self,
        stripe_client: StripeClient,
        tax_calculator: TaxCalculator,
        email_service: EmailService,
    ):
        self.stripe = stripe_client
        self.tax = tax_calculator
        self.email = email_service

    def process_payment(
        self,
        user: User,
        amount: Decimal,
        currency: str = "usd",
        description: str = "",
        idempotency_key: Optional[str] = None,
    ) -> Payment:
        """Process a payment for a user.

        Validates the user, calculates tax, charges via Stripe,
        records the payment, and sends a receipt email.

        Raises:
            ValueError: If amount is non-positive or user is inactive.
            PaymentError: If Stripe charge fails.
        """
        if amount <= 0:
            raise ValueError(f"Amount must be positive, got {amount}")

        if not user.is_active:
            raise ValueError("Cannot process payment for inactive user")

        if currency not in ("usd", "eur", "gbp", "cad", "aud"):
            raise ValueError(f"Unsupported currency: {currency}")

        tax_amount = self.tax.calculate(amount, user.billing_address)
        total = amount + tax_amount

        charge = self.stripe.create_charge(
            customer_id=user.stripe_customer_id,
            amount=int(total * 100),  # cents
            currency=currency,
            description=description,
            idempotency_key=idempotency_key,
        )

        payment = Payment(
            user_id=user.id,
            amount=amount,
            tax_amount=tax_amount,
            total=total,
            currency=currency,
            stripe_charge_id=charge["id"],
            status="completed",
            created_at=datetime.utcnow(),
        )

        self.email.send_receipt(
            to=user.email,
            payment=payment,
        )

        return payment

    def refund_payment(
        self,
        payment: Payment,
        reason: str = "",
        partial_amount: Optional[Decimal] = None,
    ) -> Payment:
        """Refund a payment, fully or partially.

        Raises:
            ValueError: If payment already refunded or partial amount exceeds original.
            RefundError: If Stripe refund fails.
        """
        if payment.status == "refunded":
            raise ValueError("Payment already refunded")

        if payment.status != "completed":
            raise ValueError(f"Cannot refund payment with status: {payment.status}")

        refund_amount = partial_amount if partial_amount else payment.total

        if refund_amount > payment.total:
            raise ValueError(f"Refund amount {refund_amount} exceeds payment total {payment.total}")

        refund = self.stripe.create_refund(
            charge_id=payment.stripe_charge_id,
            amount=int(refund_amount * 100),
            reason=reason,
        )

        if partial_amount and partial_amount < payment.total:
            payment.status = "partially_refunded"
            payment.refunded_amount = refund_amount
        else:
            payment.status = "refunded"
            payment.refunded_amount = payment.total

        payment.stripe_refund_id = refund["id"]
        payment.refunded_at = datetime.utcnow()

        self.email.send_refund_notification(
            to=payment.user.email,
            payment=payment,
            refund_amount=refund_amount,
        )

        return payment

    def generate_invoice(
        self,
        user: User,
        payments: list[Payment],
        period_start: datetime,
        period_end: datetime,
    ) -> Invoice:
        """Generate an invoice for a list of payments within a period.

        Raises:
            ValueError: If no payments provided or period is invalid.
        """
        if not payments:
            raise ValueError("Cannot generate invoice with no payments")

        if period_start >= period_end:
            raise ValueError("period_start must be before period_end")

        filtered = [
            p
            for p in payments
            if p.status in ("completed", "partially_refunded")
            and period_start <= p.created_at <= period_end
        ]

        if not filtered:
            raise ValueError("No qualifying payments in the specified period")

        subtotal = sum(p.amount for p in filtered)
        tax_total = sum(p.tax_amount for p in filtered)
        refund_total = sum(p.refunded_amount for p in filtered if p.refunded_amount)
        grand_total = subtotal + tax_total - refund_total

        invoice = Invoice(
            user_id=user.id,
            payments=filtered,
            subtotal=subtotal,
            tax_total=tax_total,
            refund_total=refund_total,
            grand_total=grand_total,
            period_start=period_start,
            period_end=period_end,
            issued_at=datetime.utcnow(),
        )

        return invoice

    def get_payment_history(
        self,
        user: User,
        days: int = 30,
        status_filter: Optional[str] = None,
    ) -> list[Payment]:
        """Get payment history for a user within a time window.

        Returns payments sorted by date descending.
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        payments = [p for p in user.payments if p.created_at >= cutoff]

        if status_filter:
            payments = [p for p in payments if p.status == status_filter]

        return sorted(payments, key=lambda p: p.created_at, reverse=True)
