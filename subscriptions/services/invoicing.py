from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Iterable, Optional

from django.db import transaction
from django.utils import timezone

from payments.utils import calculate_fees
from subscriptions.models import (
    Coupon,
    CurrencyChoices,
    Invoice,
    InvoiceLineItem,
    InvoiceStatus,
    Plan,
    Subscription,
)


class InvoiceService:
    """Create and update invoices for subscriptions."""

    def __init__(self, *, now=None):
        self._now = now or timezone.now

    def create_invoice(
        self,
        subscription: Subscription,
        *,
        status: InvoiceStatus = InvoiceStatus.DRAFT,
        coupon: Optional[Coupon] = None,
        line_items: Optional[Iterable[dict]] = None,
        period_start=None,
        period_end=None,
        due_at=None,
        metadata: Optional[dict] = None,
        memo: str = "",
    ) -> Invoice:
        period_start = period_start or subscription.current_period_start
        period_end = period_end or subscription.current_period_end

        defaults = self._build_invoice_totals(subscription, coupon, line_items)

        with transaction.atomic():
            invoice = Invoice.objects.create(
                subscription=subscription,
                user=subscription.user,
                number=self._generate_number(subscription),
                status=status,
                currency=subscription.plan.currency,
                period_start=period_start,
                period_end=period_end,
                due_at=due_at or period_end,
                metadata=metadata or {},
                memo=memo,
                **defaults,
            )

            items = line_items or [
                {
                    "plan": subscription.plan,
                    "description": subscription.plan.name,
                    "quantity": subscription.quantity,
                    "unit_amount": subscription.plan.amount,
                    "total_amount": subscription.plan.amount * subscription.quantity,
                    "metadata": {},
                }
            ]

            for item in items:
                InvoiceLineItem.objects.create(invoice=invoice, **item)

        return invoice

    def _build_invoice_totals(
        self,
        subscription: Subscription,
        coupon: Optional[Coupon],
        line_items: Optional[Iterable[dict]],
    ) -> dict:
        subtotal = self._compute_subtotal(subscription, line_items)
        discount_total = self._compute_discount(subtotal, coupon, subscription.plan.currency)

        total = (subtotal - discount_total).quantize(Decimal("0.000001"))
        platform_fee, _ = calculate_fees(total)

        return {
            "subtotal": subtotal,
            "discount_total": discount_total,
            "total": total,
            "platform_fee": platform_fee,
            "tax_total": Decimal("0"),
        }

    def _compute_subtotal(self, subscription: Subscription, line_items: Optional[Iterable[dict]]) -> Decimal:
        if line_items:
            subtotal = sum(
                Decimal(item["total_amount"])
                if not isinstance(item["total_amount"], Decimal)
                else item["total_amount"]
                for item in line_items
            )
        else:
            subtotal = subscription.plan.amount * subscription.quantity
        return subtotal.quantize(Decimal("0.000001"))

    def _compute_discount(
        self,
        subtotal: Decimal,
        coupon: Optional[Coupon],
        currency: CurrencyChoices,
    ) -> Decimal:
        if not coupon:
            return Decimal("0")

        discount = Decimal("0")
        if coupon.percent_off is not None:
            discount = (subtotal * coupon.percent_off / Decimal("100")).quantize(Decimal("0.000001"))
        elif coupon.amount_off is not None and coupon.currency == currency:
            discount = min(subtotal, coupon.amount_off)

        return discount

    def _generate_number(self, subscription: Subscription) -> str:
        return f"INV-{subscription.id}-{uuid.uuid4().hex[:8]}"
