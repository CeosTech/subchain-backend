from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from subscriptions.models import (
    CheckoutSession,
    CheckoutSessionStatus,
    Coupon,
    CurrencyChoices,
    Plan,
    PlanInterval,
    Subscription,
    SubscriptionStatus,
)
from notifications.models import Notification


class SubscriptionAPITests(APITestCase):
    def setUp(self):
        self.override_email = self.settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
        self.override_email.enable()
        self.addCleanup(self.override_email.disable)
        self.plan = Plan.objects.create(
            code="trial-plan",
            name="Trial Plan",
            amount=Decimal("5.000000"),
            currency=CurrencyChoices.ALGO,
            interval=PlanInterval.MONTH,
            trial_days=7,
        )
        self.free_plan = Plan.objects.create(
            code="free-plan",
            name="Free Plan",
            amount=Decimal("0"),
            currency=CurrencyChoices.ALGO,
            interval=PlanInterval.MONTH,
            trial_days=0,
        )
        self.user = get_user_model().objects.create_user(
            email="api@example.com",
            password="pass1234",
            username="api_user",
            wallet_address="APIWALLET",
        )
        self.client.force_authenticate(user=self.user)

    def _customer_payload(self, **overrides):
        base = {
            "customer_type": "individual",
            "billing_email": "billing@example.com",
            "billing_phone": "",
            "billing_address": "123 Billing Street",
            "billing_same_as_shipping": True,
            "shipping_address": "",
        }
        base.update(overrides)
        return base

    def test_create_subscription_with_trial(self):
        url = reverse("subscription-list")
        payload = {
            "plan_id": self.plan.id,
            "wallet_address": "TRIALWALLET",
            **self._customer_payload(),
        }

        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        subscription = Subscription.objects.get(id=response.data["subscription"]["id"])
        self.assertEqual(subscription.status, SubscriptionStatus.TRIALING)
        self.assertIsNone(response.data["payment_intent"])
        self.assertEqual(Notification.objects.filter(user=self.user).count(), 1)

    def test_create_subscription_free_plan(self):
        url = reverse("subscription-list")
        payload = {
            "plan_id": self.free_plan.id,
            "wallet_address": "FREEWALLET",
            **self._customer_payload(billing_email="freeplan@example.com"),
        }

        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        subscription = Subscription.objects.get(id=response.data["subscription"]["id"])
        self.assertEqual(subscription.status, SubscriptionStatus.ACTIVE)
        self.assertEqual(Notification.objects.filter(user=self.user).count(), 2)

    def test_checkout_session_confirm(self):
        session_url = reverse("checkoutsession-list")
        payload = {
            "plan_id": self.plan.id,
            "wallet_address": "SESSIONWALLET",
            **self._customer_payload(),
        }

        response = self.client.post(session_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        session_id = response.data["id"]

        confirm_url = reverse("checkoutsession-confirm", args=[session_id])
        confirm_response = self.client.post(confirm_url, {}, format="json")

        self.assertEqual(confirm_response.status_code, status.HTTP_200_OK)
        self.assertEqual(Subscription.objects.count(), 1)
        self.assertEqual(Notification.objects.filter(user=self.user).count(), 1)
        session = CheckoutSession.objects.get(id=session_id)
        self.assertEqual(session.status, CheckoutSessionStatus.COMPLETED)

    def test_user_can_create_coupon(self):
        url = reverse("coupon-list")
        payload = {
            "code": "PROMO10",
            "name": "Promo 10",
            "duration": "once",
            "percent_off": "10.00",
            "currency": CurrencyChoices.ALGO,
            "max_redemptions": 50,
        }

        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        coupon = Coupon.objects.get(code="PROMO10")
        self.assertEqual(coupon.created_by, self.user)

    def test_user_cannot_update_foreign_coupon(self):
        other_user = get_user_model().objects.create_user(
            email="owner@example.com",
            password="pass1234",
            username="owner",
            wallet_address="OWNERWALLET",
        )
        coupon = Coupon.objects.create(
            code="FOREIGN",
            duration="once",
            percent_off=Decimal("10.00"),
            currency=CurrencyChoices.ALGO,
            created_by=other_user,
        )

        url = reverse("coupon-detail", args=[coupon.id])
        response = self.client.patch(url, {"name": "Updated"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
