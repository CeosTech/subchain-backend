from decimal import Decimal
from datetime import timedelta
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from payments.models import Transaction
from subscriptions.models import (
    Coupon,
    CurrencyChoices,
    EventLog,
    Invoice,
    InvoiceStatus,
    PaymentIntentStatus,
    Plan,
    PlanInterval,
    Subscription,
    SubscriptionStatus,
)
from subscriptions.services import EventRecorder, InvoiceService, PaymentIntentService, SubscriptionLifecycleService


class SubscriptionLifecycleServiceTests(TestCase):
    def setUp(self):
        self.plan = Plan.objects.create(
            code="starter",
            name="Starter",
            amount=Decimal("10.000000"),
            currency=CurrencyChoices.ALGO,
            interval=PlanInterval.MONTH,
            trial_days=7,
        )
        self.user = get_user_model().objects.create_user(
            email="customer@example.com",
            password="pass1234",
            username="customer",
            wallet_address="CUSTWALLET123",
        )
        self.lifecycle = SubscriptionLifecycleService()

    def test_create_subscription_with_trial(self):
        result = self.lifecycle.create_subscription(
            user=self.user,
            plan=self.plan,
            wallet_address="WALLET",
        )

        subscription = result.subscription
        self.assertEqual(subscription.status, SubscriptionStatus.TRIALING)
        self.assertIsNotNone(subscription.trial_end_at)
        self.assertTrue(EventLog.objects.filter(resource_id=subscription.id, event_type="subscription.created").exists())

    def test_cancel_immediately(self):
        subscription = self.lifecycle.create_subscription(
            user=self.user, plan=self.plan, wallet_address="WALLET"
        ).subscription
        self.lifecycle.cancel_subscription(subscription, at_period_end=False)
        subscription.refresh_from_db()
        self.assertEqual(subscription.status, SubscriptionStatus.CANCELED)
        self.assertTrue(EventLog.objects.filter(event_type="subscription.canceled").exists())


class InvoiceServiceTests(TestCase):
    def setUp(self):
        self.plan = Plan.objects.create(
            code="pro",
            name="Pro",
            amount=Decimal("20.000000"),
            currency=CurrencyChoices.ALGO,
            interval=PlanInterval.MONTH,
        )
        self.user = get_user_model().objects.create_user(
            email="invoice@example.com",
            password="pass1234",
            username="invoice",
            wallet_address="INVWALLET",
        )
        self.subscription = Subscription.objects.create(
            user=self.user,
            plan=self.plan,
            status=SubscriptionStatus.ACTIVE,
            wallet_address="INVWALLET",
            current_period_start=timezone.now(),
            current_period_end=timezone.now() + timedelta(days=30),
        )
        self.service = InvoiceService()

    def test_create_invoice_with_coupon(self):
        coupon = Coupon.objects.create(
            code="PROMO10",
            percent_off=Decimal("10"),
            currency=CurrencyChoices.ALGO,
            duration="once",
        )
        invoice = self.service.create_invoice(self.subscription, coupon=coupon)
        self.assertEqual(invoice.subtotal, Decimal("20.000000"))
        self.assertEqual(invoice.discount_total, Decimal("2.000000"))
        self.assertEqual(invoice.total, Decimal("18.000000"))
        self.assertEqual(invoice.line_items.count(), 1)


class PaymentIntentServiceTests(TestCase):
    def setUp(self):
        self.plan = Plan.objects.create(
            code="enterprise",
            name="Enterprise",
            amount=Decimal("100.000000"),
            currency=CurrencyChoices.ALGO,
            interval=PlanInterval.MONTH,
        )
        self.user = get_user_model().objects.create_user(
            email="pay@example.com",
            password="pass1234",
            username="pay",
            wallet_address="PAYWALLET",
        )
        self.subscription = Subscription.objects.create(
            user=self.user,
            plan=self.plan,
            status=SubscriptionStatus.ACTIVE,
            wallet_address="PAYWALLET",
            current_period_start=timezone.now(),
            current_period_end=timezone.now() + timedelta(days=30),
        )
        self.invoice = Invoice.objects.create(
            subscription=self.subscription,
            user=self.user,
            number="INV-PI-1",
            status=InvoiceStatus.OPEN,
            currency=CurrencyChoices.ALGO,
            subtotal=self.plan.amount,
            total=self.plan.amount,
            discount_total=Decimal("0"),
        )

    def test_process_invoice_success(self):
        swap_result = {
            "status": "success",
            "algo_sent": 1_000_000,
            "usdc_received": 950_000,
            "tx_ids": ["TX123"],
            "confirmed_round": 12345,
        }
        service = PaymentIntentService(
            event_recorder=EventRecorder(),
            swap_executor=mock.Mock(return_value=swap_result),
            swap_error_class=Exception,
        )

        payment_intent = service.process_invoice(self.invoice)
        self.invoice.refresh_from_db()
        self.assertEqual(payment_intent.status, PaymentIntentStatus.SUCCEEDED)
        self.assertEqual(self.invoice.status, InvoiceStatus.PAID)
        self.assertTrue(EventLog.objects.filter(event_type="invoice.paid").exists())
        self.assertEqual(payment_intent.usdc_received, Decimal("0.950000"))
        self.assertEqual(Transaction.objects.count(), 1)

    def test_process_invoice_failure(self):
        def failing_swap(_txn):
            raise RuntimeError("network error")

        service = PaymentIntentService(
            event_recorder=EventRecorder(),
            swap_executor=failing_swap,
            swap_error_class=RuntimeError,
        )

        with self.assertRaises(RuntimeError):
            service.process_invoice(self.invoice)

        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, InvoiceStatus.OPEN)
        self.assertTrue(EventLog.objects.filter(event_type="invoice.payment_failed").exists())
