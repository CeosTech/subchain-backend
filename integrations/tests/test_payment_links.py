from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from integrations.models import EndpointPricingRule, PaymentLink, PaymentLinkEvent, PaymentReceipt, X402CreditPlan, CreditSubscription


def fake_verifier(receipt: str, price: Decimal, request):
    if not receipt:
        return None
    return {
        "nonce": receipt,
        "amount": str(price),
        "status": "confirmed",
        "payer": "payer-wallet",
        "transaction_id": "TEST-TX",
    }


@override_settings(
    X402_ENABLED=True,
    X402_PAYTO_ADDRESS="TEST_PAYTO",
    X402_DEFAULT_PRICE="0",
    X402_PRICING_RULES="{}",
    X402_RECEIPT_VERIFIER="integrations.tests.test_payment_links.fake_verifier",
)
class PaymentLinkFlowTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(email="tenant@example.com", password="pass12345")
        self.client.force_login(self.user)
        self.api_client = APIClient()
        self.api_client.force_authenticate(self.user)

    def test_create_link_and_process_payment(self):
        payload = {
            "name": "Premium Report",
            "description": "Access to premium analytics",
            "amount": "0.75",
            "currency": "USDC",
            "network": "algorand",
            "success_url": "https://example.com/success",
            "pay_to_address": "TENANT_WALLET",
            "platform_fee_percent": "15",
            "metadata": {"resource": "report-2025"},
        }
        response = self.api_client.post("/api/integrations/x402/links/", payload, format="json")
        self.assertEqual(response.status_code, 201, response.content)
        link = PaymentLink.objects.get(user=self.user)
        rule = EndpointPricingRule.objects.filter(user=self.user, pattern=link.pattern).first()
        self.assertIsNotNone(rule)
        self.assertEqual(rule.amount, Decimal("0.75"))
        self.assertEqual(rule.metadata.get("pay_to_address"), "TENANT_WALLET")

        # First call triggers 402 challenge
        initial = self.client.get(f"/paywall/tenant/{self.user.id}/links/{link.slug}/")
        self.assertEqual(initial.status_code, 402)
        nonce = initial["X-402-Nonce"]
        self.assertEqual(initial["X-402-PayTo"], "TENANT_WALLET")

        paid = self.client.get(
            f"/paywall/tenant/{self.user.id}/links/{link.slug}/",
            HTTP_X_402_RECEIPT=nonce,
        )
        self.assertEqual(paid.status_code, 200)
        payload = paid.json()
        self.assertEqual(payload["name"], "Premium Report")
        self.assertIn("receipt_id", payload)

        receipt = PaymentReceipt.objects.get(id=payload["receipt_id"])
        self.assertEqual(receipt.status, "confirmed")
        event = PaymentLinkEvent.objects.filter(link=link, receipt=receipt).first()
        self.assertIsNotNone(event)
        self.assertEqual(event.payer_address, "payer-wallet")
        self.assertEqual(str(event.fee_amount), "0.11250000")
        self.assertEqual(str(event.merchant_amount), "0.63750000")

    def test_credit_plan_top_up(self):
        plan_payload = {
            "name": "API Credits",
            "description": "Pack of credits",
            "amount": "1.25",
            "currency": "USDC",
            "network": "algorand",
            "credits_per_payment": 10,
            "pay_to_address": "TENANT_WALLET",
            "platform_fee_percent": "20",
        }
        response = self.api_client.post("/api/integrations/x402/credit-plans/", plan_payload, format="json")
        self.assertEqual(response.status_code, 201, response.content)
        plan = X402CreditPlan.objects.get(user=self.user)
        self.assertEqual(plan.platform_fee_percent, Decimal("20"))

        initial = self.client.get(f"/paywall/tenant/{self.user.id}/credits/{plan.slug}/", {"consumer": "wallet-123"})
        self.assertEqual(initial.status_code, 402)
        nonce = initial["X-402-Nonce"]
        self.assertEqual(initial["X-402-PayTo"], "TENANT_WALLET")

        paid = self.client.get(
            f"/paywall/tenant/{self.user.id}/credits/{plan.slug}/",
            {"consumer": "wallet-123"},
            HTTP_X_402_RECEIPT=nonce,
        )
        self.assertEqual(paid.status_code, 200)
        payload = paid.json()
        self.assertEqual(payload["plan"]["credits_per_payment"], 10)
        self.assertEqual(payload["consumer"], "wallet-123")

        subscription = CreditSubscription.objects.get(plan=plan, consumer_ref="wallet-123")
        self.assertEqual(subscription.credits_remaining, 10)
        self.assertEqual(subscription.total_credits, 10)

        consume = self.api_client.post(
            f"/api/integrations/x402/credit-subscriptions/{subscription.id}/consume/",
            {"credits": 4, "description": "API call"},
            format="json",
        )
        self.assertEqual(consume.status_code, 201, consume.content)
        subscription.refresh_from_db()
        self.assertEqual(subscription.credits_remaining, 6)
        top_up_usage = subscription.usages.filter(usage_type="top_up").first()
        self.assertIsNotNone(top_up_usage)
        self.assertEqual(str(top_up_usage.fee_amount), "0.25000000")
        self.assertEqual(str(top_up_usage.merchant_amount), "1.00000000")
