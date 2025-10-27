from django.core.management.base import BaseCommand
from django.utils import timezone

from payments.models import TransactionType
from payments.services import SwapExecutionError
from subscriptions.models import InvoiceStatus, Subscription, SubscriptionStatus
from subscriptions.services import InvoiceService, PaymentIntentService, SubscriptionLifecycleService


class Command(BaseCommand):
    help = "End trials that have reached their deadline and attempt first billing."

    def handle(self, *args, **options):
        lifecycle = SubscriptionLifecycleService()
        invoicing = InvoiceService()
        payment_service = PaymentIntentService()

        queryset = (
            Subscription.objects.select_related("plan", "coupon", "user")
            .filter(
                status=SubscriptionStatus.TRIALING,
                trial_end_at__isnull=False,
                trial_end_at__lte=timezone.now(),
            )
        )

        if not queryset.exists():
            self.stdout.write("No trials to expire.")
            return

        for subscription in queryset:
            plan_amount = subscription.plan.amount

            invoice = invoicing.create_invoice(
                subscription,
                status=InvoiceStatus.OPEN,
                coupon=subscription.coupon,
            )

            if plan_amount <= 0:
                lifecycle.activate_subscription(subscription)
                invoice.status = InvoiceStatus.PAID
                invoice.paid_at = timezone.now()
                invoice.save(update_fields=["status", "paid_at"])
                self.stdout.write(self.style.SUCCESS(f"Subscription {subscription.id} activated (plan free)."))
                continue

            try:
                payment_service.process_invoice(invoice, transaction_type=TransactionType.SUBSCRIPTION)
                lifecycle.activate_subscription(subscription)
                self.stdout.write(self.style.SUCCESS(f"Subscription {subscription.id} activated and billed."))
            except SwapExecutionError as exc:
                lifecycle.mark_past_due(subscription, reason=str(exc))
                self.stdout.write(self.style.WARNING(f"Subscription {subscription.id} moved to past_due: {exc}"))
