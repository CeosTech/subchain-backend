from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Dict, Optional

from django.db import transaction
from django.utils import timezone

from .models import (
    CreditSubscription,
    CreditUsage,
    CreditUsageType,
    DeliveryStatus,
    EndpointPricingRule,
    Integration,
    IntegrationDeliveryLog,
    PaymentLink,
    PaymentLinkEvent,
    PaymentReceipt,
    X402CreditPlan,
)

logger = logging.getLogger(__name__)


def record_delivery(
    *,
    integration: Integration,
    event_type: str,
    payload: Optional[Dict[str, Any]] = None,
    status: str = DeliveryStatus.SUCCESS,
    response_code: Optional[int] = None,
    response_body: str = "",
    error_message: str = "",
    duration_ms: Optional[int] = None,
) -> IntegrationDeliveryLog:
    """Persist a delivery attempt and update integration health."""

    log_entry = IntegrationDeliveryLog.objects.create(
        integration=integration,
        event_type=event_type,
        payload=payload or {},
        status=status,
        response_code=response_code,
        response_body=response_body[:2000],
        error_message=error_message[:2000],
        duration_ms=duration_ms,
    )

    if status == DeliveryStatus.SUCCESS:
        integration.mark_success()
    else:
        integration.mark_failure(error_message)

    logger.info(
        "Integration delivery %s for %s (%s)",
        status,
        integration.name,
        event_type,
    )
    return log_entry


def simulate_delivery(integration: Integration, event_type: str, payload: Optional[Dict[str, Any]] = None) -> IntegrationDeliveryLog:
    """Utility function for admin/test actions to record a successful delivery."""
    return record_delivery(
        integration=integration,
        event_type=event_type,
        payload=payload or {"test": timezone.now().isoformat()},
        status=DeliveryStatus.SUCCESS,
    )


def sync_pricing_rule_for_link(link: PaymentLink) -> EndpointPricingRule:
    methods = ["GET"]
    pattern = link.get_paywall_path()
    rule, _ = EndpointPricingRule.objects.update_or_create(
        user=link.user,
        pattern=pattern,
        defaults={
            "methods": methods,
            "amount": link.amount,
            "currency": link.currency,
            "network": link.network,
            "is_active": link.is_active,
            "description": link.description[:250],
            "metadata": {
                "link_id": link.id,
                "kind": link.kind,
                "pay_to_address": link.pay_to_address,
                "platform_fee_percent": str(link.platform_fee_percent),
            },
        },
    )
    return rule


def sync_pricing_rule_for_credit_plan(plan: X402CreditPlan) -> EndpointPricingRule:
    pattern = plan.build_pattern()
    rule, _ = EndpointPricingRule.objects.update_or_create(
        user=plan.user,
        pattern=pattern,
        defaults={
            "methods": ["GET"],
            "amount": plan.amount,
            "currency": plan.currency,
            "network": plan.network,
            "is_active": plan.is_active,
            "description": plan.description[:250],
            "metadata": {
                "credit_plan_id": plan.id,
                "credits_per_payment": plan.credits_per_payment,
                "pay_to_address": plan.pay_to_address,
                "platform_fee_percent": str(plan.platform_fee_percent),
            },
        },
    )
    return rule


def deactivate_pricing_rule(user_id: int, pattern: str) -> None:
    EndpointPricingRule.objects.filter(user_id=user_id, pattern=pattern).update(is_active=False)


def _quantize_amount(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.00000001"))


def _compute_fee(amount: Decimal, fee_percent: Decimal) -> tuple[Decimal, Decimal]:
    if fee_percent:
        fee = _quantize_amount((amount * fee_percent) / Decimal("100"))
    else:
        fee = _quantize_amount(Decimal("0"))
    merchant = _quantize_amount(amount - fee)
    return fee, merchant


def record_payment_link_event(
    *,
    link: PaymentLink,
    receipt: PaymentReceipt,
    payer: str | None,
    metadata: Optional[Dict[str, Any]] = None,
) -> PaymentLinkEvent:
    fee_percent = Decimal(str(link.platform_fee_percent or 0))
    fee_amount, merchant_amount = _compute_fee(receipt.amount, fee_percent)
    with transaction.atomic():
        event, created = PaymentLinkEvent.objects.get_or_create(
            link=link,
            receipt=receipt,
            defaults={
                "payer_address": payer or "",
                "amount": receipt.amount,
                "fee_amount": fee_amount,
                "merchant_amount": merchant_amount,
                "metadata": metadata or {},
            },
        )
        if not created:
            updated = False
            if payer and event.payer_address != payer:
                event.payer_address = payer
                updated = True
            if metadata:
                combined = event.metadata.copy()
                combined.update(metadata)
                event.metadata = combined
                updated = True
            if event.fee_amount != fee_amount:
                event.fee_amount = fee_amount
                updated = True
            if event.merchant_amount != merchant_amount:
                event.merchant_amount = merchant_amount
                updated = True
            if updated:
                event.save(update_fields=["payer_address", "metadata", "fee_amount", "merchant_amount"])
    return event


def apply_credit_top_up(
    *,
    plan: X402CreditPlan,
    consumer_ref: str,
    receipt: PaymentReceipt,
    metadata: Optional[Dict[str, Any]] = None,
) -> CreditUsage:
    fee_percent = Decimal(str(plan.platform_fee_percent or 0))
    fee_amount, merchant_amount = _compute_fee(receipt.amount, fee_percent)
    metadata = metadata or {}
    metadata.setdefault("fee_amount", str(fee_amount))
    metadata.setdefault("merchant_amount", str(merchant_amount))

    with transaction.atomic():
        subscription, created = CreditSubscription.objects.select_for_update().get_or_create(
            plan=plan,
            consumer_ref=consumer_ref,
            defaults={
                "credits_remaining": plan.credits_per_payment,
                "total_credits": plan.credits_per_payment,
                "last_purchase_at": timezone.now(),
                "metadata": metadata or {},
            },
        )
        if not created:
            subscription.credits_remaining += plan.credits_per_payment
            subscription.total_credits += plan.credits_per_payment
            subscription.last_purchase_at = timezone.now()
            if metadata:
                combined = subscription.metadata.copy()
                combined.update(metadata)
                subscription.metadata = combined
            subscription.save(update_fields=["credits_remaining", "total_credits", "last_purchase_at", "metadata", "updated_at"])

        usage = CreditUsage.objects.create(
            subscription=subscription,
            receipt=receipt,
            usage_type=CreditUsageType.TOP_UP,
            credits_delta=plan.credits_per_payment,
            fee_amount=fee_amount,
            merchant_amount=merchant_amount,
            metadata=metadata,
        )
    return usage
