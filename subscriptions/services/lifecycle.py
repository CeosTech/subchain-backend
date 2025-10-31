from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Optional

from django.db import transaction
from django.utils import timezone

from subscriptions.models import Coupon, Plan, PlanInterval, Subscription, SubscriptionStatus, CustomerType
from subscriptions.services.events import EventRecorder
from subscriptions.services.invoicing import InvoiceService
from subscriptions.services.notification import NotificationDispatcher
from algorand.subscription import opt_in_subscription, SubscriptionAccount


def _calculate_period_end(start, interval: str) -> timezone.datetime:
    if interval == PlanInterval.YEAR:
        return start + timedelta(days=365)
    # Default monthly billing to 30 days to avoid new dependencies.
    return start + timedelta(days=30)


@dataclass
class LifecycleResult:
    subscription: Subscription


class SubscriptionLifecycleService:
    def __init__(
        self,
        *,
        invoice_service: Optional[InvoiceService] = None,
        event_recorder: Optional[EventRecorder] = None,
        notification_dispatcher: Optional[NotificationDispatcher] = None,
        now=None,
    ):
        self.invoice_service = invoice_service or InvoiceService()
        self.events = event_recorder or EventRecorder()
        self.notifications = notification_dispatcher or NotificationDispatcher()
        self._now = now or timezone.now

    def create_subscription(
        self,
        *,
        user,
        plan: Plan,
        wallet_address: str,
        coupon: Optional[Coupon] = None,
        quantity: int = 1,
        metadata: Optional[dict] = None,
        customer_type: CustomerType = CustomerType.INDIVIDUAL,
        company_name: str = "",
        vat_number: str = "",
        billing_email: str | None = None,
        billing_phone: str = "",
        billing_address: str = "",
        billing_same_as_shipping: bool = True,
        shipping_address: str = "",
    ) -> LifecycleResult:
        now = self._now()
        trial_days = plan.trial_days
        trial_end = now + timedelta(days=trial_days) if trial_days else None

        current_period_start = now
        current_period_end = trial_end or _calculate_period_end(now, plan.interval)
        status = SubscriptionStatus.TRIALING if trial_end else SubscriptionStatus.ACTIVE

        with transaction.atomic():
            subscription = Subscription.objects.create(
                user=user,
                plan=plan,
                coupon=coupon,
                status=status,
                wallet_address=wallet_address,
                quantity=quantity,
                trial_end_at=trial_end,
                current_period_start=current_period_start,
                current_period_end=current_period_end,
                metadata=metadata or {},
                customer_type=customer_type or CustomerType.INDIVIDUAL,
                company_name=company_name,
                vat_number=vat_number,
                billing_email=billing_email or "",
                billing_phone=billing_phone,
                billing_address=billing_address,
                billing_same_as_shipping=billing_same_as_shipping,
                shipping_address=shipping_address if not billing_same_as_shipping else "",
            )

            self.events.record(
                "subscription.created",
                resource_type="subscription",
                resource_id=subscription.id,
                payload={
                    "plan": plan.code,
                    "status": subscription.status,
                    "trial_end_at": subscription.trial_end_at.isoformat() if subscription.trial_end_at else None,
                },
            )

            self.notifications.subscription_created(subscription)

        # Attempt on-chain opt-in (best effort)
        if plan.contract_app_id:
            try:
                subscription_account = SubscriptionAccount(address=wallet_address, private_key="")
                opt_in_subscription(subscription, subscription_account)
            except Exception as exc:
                logger.warning("Failed to opt-in subscription %s: %s", subscription.id, exc)

        return LifecycleResult(subscription=subscription)

    def activate_subscription(self, subscription: Subscription) -> LifecycleResult:
        if subscription.status == SubscriptionStatus.ACTIVE:
            return LifecycleResult(subscription=subscription)

        subscription.status = SubscriptionStatus.ACTIVE
        subscription.trial_end_at = None
        subscription.current_period_start = self._now()
        subscription.current_period_end = _calculate_period_end(subscription.current_period_start, subscription.plan.interval)
        subscription.save(update_fields=["status", "trial_end_at", "current_period_start", "current_period_end", "updated_at"])

        self.events.record(
            "subscription.activated",
            resource_type="subscription",
            resource_id=subscription.id,
            payload={"plan": subscription.plan.code},
        )

        self.notifications.subscription_activated(subscription)

        return LifecycleResult(subscription=subscription)

    def cancel_subscription(self, subscription: Subscription, *, at_period_end: bool = True) -> LifecycleResult:
        now = self._now()
        if at_period_end:
            subscription.cancel_at_period_end = True
            subscription.save(update_fields=["cancel_at_period_end", "updated_at"])
            event_payload = {"cancel_at_period_end": True, "current_period_end": subscription.current_period_end}
            self.notifications.subscription_canceled(subscription, immediate=False)
        else:
            subscription.status = SubscriptionStatus.CANCELED
            subscription.canceled_at = now
            subscription.ended_at = now
            subscription.save(update_fields=["status", "canceled_at", "ended_at", "updated_at"])
            event_payload = {"cancelled_immediately": True}
            self.notifications.subscription_canceled(subscription, immediate=True)

        self.events.record(
            "subscription.canceled",
            resource_type="subscription",
            resource_id=subscription.id,
            payload=event_payload,
        )
        return LifecycleResult(subscription=subscription)

    def mark_past_due(self, subscription: Subscription, reason: str | None = None) -> LifecycleResult:
        subscription.status = SubscriptionStatus.PAST_DUE
        subscription.save(update_fields=["status", "updated_at"])

        self.events.record(
            "subscription.past_due",
            resource_type="subscription",
            resource_id=subscription.id,
            payload={"reason": reason},
        )
        self.notifications.subscription_past_due(subscription, reason)
        return LifecycleResult(subscription=subscription)

    def resume_subscription(self, subscription: Subscription) -> LifecycleResult:
        subscription.status = SubscriptionStatus.ACTIVE
        subscription.cancel_at_period_end = False
        subscription.canceled_at = None
        subscription.ended_at = None
        subscription.current_period_start = self._now()
        subscription.current_period_end = _calculate_period_end(subscription.current_period_start, subscription.plan.interval)
        subscription.save(
            update_fields=[
                "status",
                "cancel_at_period_end",
                "canceled_at",
                "ended_at",
                "current_period_start",
                "current_period_end",
                "updated_at",
            ]
        )

        self.events.record(
            "subscription.resumed",
            resource_type="subscription",
            resource_id=subscription.id,
            payload={"plan": subscription.plan.code},
        )
        self.notifications.subscription_resumed(subscription)
        return LifecycleResult(subscription=subscription)

    def advance_period(self, subscription: Subscription) -> LifecycleResult:
        if subscription.cancel_at_period_end:
            return self.finalize_cancellation(subscription)

        now = self._now()
        subscription.status = SubscriptionStatus.ACTIVE
        subscription.current_period_start = now
        subscription.current_period_end = _calculate_period_end(now, subscription.plan.interval)
        subscription.save(
            update_fields=[
                "status",
                "current_period_start",
                "current_period_end",
                "updated_at",
            ]
        )

        self.events.record(
            "subscription.renewed",
            resource_type="subscription",
            resource_id=subscription.id,
            payload={"plan": subscription.plan.code},
        )
        self.notifications.subscription_renewed(subscription)
        return LifecycleResult(subscription=subscription)

    def finalize_cancellation(self, subscription: Subscription) -> LifecycleResult:
        now = self._now()
        subscription.status = SubscriptionStatus.CANCELED
        subscription.canceled_at = subscription.canceled_at or now
        subscription.ended_at = now
        subscription.cancel_at_period_end = False
        subscription.save(update_fields=["status", "canceled_at", "ended_at", "cancel_at_period_end", "updated_at"])

        self.events.record(
            "subscription.ended",
            resource_type="subscription",
            resource_id=subscription.id,
            payload={"ended_at": subscription.ended_at.isoformat()},
        )
        self.notifications.subscription_ended(subscription)
        return LifecycleResult(subscription=subscription)
