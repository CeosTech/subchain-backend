from django.core.management.base import BaseCommand

from payments.models import TransactionType
from payments.services import SwapExecutionError
from subscriptions.models import Invoice, InvoiceStatus, SubscriptionStatus
from subscriptions.services import PaymentIntentService, SubscriptionLifecycleService


class Command(BaseCommand):
    help = "Retry payments for invoices linked to past-due subscriptions."

    def handle(self, *args, **options):
        invoices = (
            Invoice.objects.select_related("subscription", "subscription__plan", "subscription__coupon", "user")
            .filter(
                status__in=[InvoiceStatus.OPEN, InvoiceStatus.UNCOLLECTIBLE],
                subscription__status=SubscriptionStatus.PAST_DUE,
            )
        )

        if not invoices.exists():
            self.stdout.write("No invoices to retry.")
            return

        lifecycle = SubscriptionLifecycleService()
        payment_service = PaymentIntentService()

        for invoice in invoices:
            subscription = invoice.subscription
            try:
                payment_service.process_invoice(invoice, transaction_type=TransactionType.RENEWAL)
                lifecycle.advance_period(subscription)
                self.stdout.write(self.style.SUCCESS(f"Invoice {invoice.number} paid. Subscription {subscription.id} renewed."))
            except SwapExecutionError as exc:
                lifecycle.mark_past_due(subscription, reason=str(exc))
                self.stdout.write(self.style.WARNING(f"Payment failed for invoice {invoice.number}: {exc}"))
