from decimal import Decimal
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from subscriptions.models import (
    CurrencyChoices,
    Invoice,
    InvoiceLineItem,
    Plan,
    PlanInterval,
    Subscription,
    SubscriptionStatus,
)


class SubscriptionModelTests(TestCase):
    def setUp(self):
        self.plan = Plan.objects.create(
            code="pro-monthly",
            name="Pro Monthly",
            description="Monthly subscription",
            amount=Decimal("50.000000"),
            currency=CurrencyChoices.ALGO,
            interval=PlanInterval.MONTH,
            trial_days=14,
        )
        self.user = get_user_model().objects.create_user(
            email="member@example.com",
            password="pass1234",
            username="member",
            wallet_address="MEMBERWALLET123",
        )

    def test_subscription_defaults(self):
        subscription = Subscription.objects.create(
            user=self.user,
            plan=self.plan,
            status=SubscriptionStatus.TRIALING,
            wallet_address="WALLET123",
            trial_end_at=timezone.now() + timedelta(days=14),
        )

        self.assertEqual(subscription.plan, self.plan)
        self.assertTrue(subscription.is_active)
        self.assertEqual(subscription.quantity, 1)
        self.assertIsNone(subscription.current_period_end)

    def test_invoice_line_items_total(self):
        subscription = Subscription.objects.create(
            user=self.user,
            plan=self.plan,
            status=SubscriptionStatus.ACTIVE,
            wallet_address="WALLET123",
            current_period_start=timezone.now(),
            current_period_end=timezone.now() + timedelta(days=30),
        )

        invoice = Invoice.objects.create(
            subscription=subscription,
            user=self.user,
            number="INV-001",
            status="draft",
            currency=CurrencyChoices.ALGO,
            subtotal=Decimal("0"),
            total=Decimal("0"),
        )

        InvoiceLineItem.objects.create(
            invoice=invoice,
            plan=self.plan,
            description="Subscription fee",
            quantity=1,
            unit_amount=self.plan.amount,
            total_amount=self.plan.amount,
        )

        invoice.refresh_from_db()
        self.assertEqual(invoice.line_items.count(), 1)
