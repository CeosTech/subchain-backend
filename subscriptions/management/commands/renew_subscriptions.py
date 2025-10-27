from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from payments.models import TransactionType
from payments.services import SwapExecutionError
from subscriptions.models import InvoiceStatus, Subscription, SubscriptionStatus
from subscriptions.services import InvoiceService, PaymentIntentService, SubscriptionLifecycleService


class Command(BaseCommand):
    help = "Process renewals for subscriptions whose period has ended."

    def handle(self, *args, **options):
        now = timezone.now()
        lifecycle = SubscriptionLifecycleService()
        invoicing = InvoiceService()
        payment_service = PaymentIntentService()

        queryset = (
            Subscription.objects.select_related("plan", "user", "coupon")
            .filter(
                status__in=[SubscriptionStatus.ACTIVE, SubscriptionStatus.PAST_DUE],
                current_period_end__lte=now,
            )
        )

        if not queryset.exists():
            self.stdout.write("No subscriptions to renew.")
            return

        for subscription in queryset:
            if subscription.cancel_at_period_end and subscription.current_period_end <= now:
                lifecycle.finalize_cancellation(subscription)
                self.stdout.write(f"Subscription {subscription.id} canceled at period end.")
                continue

            with transaction.atomic():
                invoice = invoicing.create_invoice(
                    subscription,
                    status=InvoiceStatus.OPEN,
                    coupon=subscription.coupon,
                )
                try:
                    payment_service.process_invoice(invoice, transaction_type=TransactionType.RENEWAL)
                    lifecycle.advance_period(subscription)
                    self.stdout.write(self.style.SUCCESS(f"Subscription {subscription.id} renewed."))
                except SwapExecutionError as exc:
                    lifecycle.mark_past_due(subscription, reason=str(exc))
                    self.stdout.write(self.style.WARNING(f"Subscription {subscription.id} payment failed: {exc}"))
