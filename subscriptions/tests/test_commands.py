from decimal import Decimal
from datetime import timedelta
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from payments.services import SwapExecutionError
from subscriptions.models import (
    CurrencyChoices,
    Invoice,
    InvoiceStatus,
    Plan,
    PlanInterval,
    Subscription,
    SubscriptionStatus,
)
from notifications.models import Notification


class CommandTests(TestCase):
    def setUp(self):
        self.override_email = self.settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
        self.override_email.enable()
        self.addCleanup(self.override_email.disable)
        self.plan_paid = Plan.objects.create(
            code="paid",
            name="Paid",
            amount=Decimal("10.000000"),
            currency=CurrencyChoices.ALGO,
            interval=PlanInterval.MONTH,
            trial_days=7,
        )
        self.plan_free = Plan.objects.create(
            code="free",
            name="Free",
            amount=Decimal("0"),
            currency=CurrencyChoices.ALGO,
            interval=PlanInterval.MONTH,
            trial_days=7,
        )
        self.user = get_user_model().objects.create_user(
            email="command@example.com",
            password="pass1234",
            username="command",
            wallet_address="COMMANDWALLET",
        )

    @mock.patch("subscriptions.management.commands.expire_trials.PaymentIntentService")
    def test_expire_trials_free_plan(self, mock_payment_service):
        subscription = Subscription.objects.create(
            user=self.user,
            plan=self.plan_free,
            status=SubscriptionStatus.TRIALING,
            wallet_address=self.user.wallet_address,
            trial_end_at=timezone.now() - timedelta(days=1),
        )

        call_command("expire_trials")

        subscription.refresh_from_db()
        self.assertEqual(subscription.status, SubscriptionStatus.ACTIVE)
        self.assertFalse(mock_payment_service.called)
        self.assertGreaterEqual(Notification.objects.count(), 1)

    @mock.patch("subscriptions.management.commands.expire_trials.PaymentIntentService")
    def test_expire_trials_paid_plan_success(self, mock_payment_service):
        subscription = Subscription.objects.create(
            user=self.user,
            plan=self.plan_paid,
            status=SubscriptionStatus.TRIALING,
            wallet_address=self.user.wallet_address,
            trial_end_at=timezone.now() - timedelta(days=1),
        )

        mock_payment_service.return_value.process_invoice.return_value = mock.Mock(status="succeeded")

        call_command("expire_trials")

        subscription.refresh_from_db()
        self.assertEqual(subscription.status, SubscriptionStatus.ACTIVE)
        self.assertTrue(mock_payment_service.return_value.process_invoice.called)
        self.assertGreaterEqual(Notification.objects.count(), 1)

    @mock.patch("subscriptions.management.commands.expire_trials.PaymentIntentService")
    def test_expire_trials_paid_plan_failure(self, mock_payment_service):
        subscription = Subscription.objects.create(
            user=self.user,
            plan=self.plan_paid,
            status=SubscriptionStatus.TRIALING,
            wallet_address=self.user.wallet_address,
            trial_end_at=timezone.now() - timedelta(days=1),
        )

        mock_payment_service.return_value.process_invoice.side_effect = SwapExecutionError("swap failed")

        call_command("expire_trials")

        subscription.refresh_from_db()
        self.assertEqual(subscription.status, SubscriptionStatus.PAST_DUE)
        self.assertGreaterEqual(Notification.objects.count(), 1)

    @mock.patch("subscriptions.management.commands.retry_failed_payments.PaymentIntentService")
    def test_retry_failed_payments_success(self, mock_payment_service):
        subscription = Subscription.objects.create(
            user=self.user,
            plan=self.plan_paid,
            status=SubscriptionStatus.PAST_DUE,
            wallet_address=self.user.wallet_address,
            current_period_start=timezone.now() - timedelta(days=30),
            current_period_end=timezone.now() - timedelta(days=1),
        )
        invoice = Invoice.objects.create(
            subscription=subscription,
            user=self.user,
            number="INV-RETRY",
            status=InvoiceStatus.OPEN,
            currency=CurrencyChoices.ALGO,
            subtotal=Decimal("10.000000"),
            total=Decimal("10.000000"),
        )
        mock_payment_service.return_value.process_invoice.return_value = mock.Mock(status="succeeded")

        call_command("retry_failed_payments")

        subscription.refresh_from_db()
        invoice.refresh_from_db()
        self.assertEqual(subscription.status, SubscriptionStatus.ACTIVE)
        self.assertEqual(invoice.status, InvoiceStatus.PAID)
        self.assertGreaterEqual(Notification.objects.count(), 1)

    @mock.patch("subscriptions.management.commands.retry_failed_payments.PaymentIntentService")
    def test_retry_failed_payments_failure(self, mock_payment_service):
        subscription = Subscription.objects.create(
            user=self.user,
            plan=self.plan_paid,
            status=SubscriptionStatus.PAST_DUE,
            wallet_address=self.user.wallet_address,
            current_period_start=timezone.now() - timedelta(days=30),
            current_period_end=timezone.now() - timedelta(days=1),
        )
        Invoice.objects.create(
            subscription=subscription,
            user=self.user,
            number="INV-RETRY-FAIL",
            status=InvoiceStatus.OPEN,
            currency=CurrencyChoices.ALGO,
            subtotal=Decimal("10.000000"),
            total=Decimal("10.000000"),
        )
        mock_payment_service.return_value.process_invoice.side_effect = SwapExecutionError("swap failed")

        call_command("retry_failed_payments")

        subscription.refresh_from_db()
        self.assertEqual(subscription.status, SubscriptionStatus.PAST_DUE)
        self.assertGreaterEqual(Notification.objects.count(), 1)
