from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.test import RequestFactory, TestCase, override_settings
from django.urls import path
from rest_framework.test import APIClient

from integrations import x402
from integrations.models import EndpointPricingRule, PaymentReceipt


def protected_view(request):
    return JsonResponse({"ok": True})


urlpatterns = [
    path("pricing-protected/", protected_view),
]


def fake_verifier(receipt: str, price: Decimal, request):
    if not receipt:
        return None
    return {
        "nonce": receipt,
        "amount": str(price),
        "status": "confirmed",
        "transaction_id": "TEST-TX",
        "payer": "payer-address",
    }


@override_settings(
    ROOT_URLCONF=__name__,
    X402_ENABLED=True,
    X402_PAYTO_ADDRESS="TEST_PAYTO",
    X402_DEFAULT_PRICE="0",
    X402_PRICING_RULES="{}",
    X402_RECEIPT_VERIFIER="integrations.tests.test_x402_pricing.fake_verifier",
    X402_NONCE_TTL_SECONDS=30,
)
class X402PricingAPITests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(email="pricing@example.com", password="pass1234")
        self.client.force_login(self.user)
        self.api_client = APIClient()
        self.api_client.force_authenticate(self.user)
        self.factory = RequestFactory()

    def test_user_can_create_pricing_rule_via_api(self):
        payload = {
            "pattern": "/pricing-protected",
            "methods": ["GET"],
            "amount": "0.90",
            "currency": "USDC",
            "network": "algorand",
            "priority": 10,
            "description": "Test rule",
        }

        response = self.api_client.post("/api/integrations/x402/pricing-rules/", payload, format="json")
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(EndpointPricingRule.objects.filter(user=self.user).count(), 1)

    def test_dynamic_pricing_applies_to_authenticated_user(self):
        EndpointPricingRule.objects.create(
            user=self.user,
            pattern="/pricing-protected",
            methods=["GET"],
            amount=Decimal("1.25"),
            currency="USDC",
            network="algorand",
            priority=5,
        )

        request = self.factory.get("/pricing-protected/")
        request.user = self.user

        price = x402.match_price("/pricing-protected/", "GET", request)
        self.assertEqual(price, Decimal("1.25"))

    def test_receipt_persistence_and_listing(self):
        EndpointPricingRule.objects.create(
            user=self.user,
            pattern="/pricing-protected",
            methods=["GET"],
            amount=Decimal("0.55"),
            currency="USDC",
            network="algorand",
            priority=5,
        )

        challenge = self.client.get("/pricing-protected/")
        self.assertEqual(challenge.status_code, 402)
        nonce = challenge["X-402-Nonce"]

        success = self.client.get("/pricing-protected/", HTTP_X_402_RECEIPT=nonce)
        self.assertEqual(success.status_code, 200)

        receipts = PaymentReceipt.objects.filter(user=self.user)
        self.assertEqual(receipts.count(), 1)
        receipt = receipts.first()
        self.assertEqual(receipt.status, "confirmed")
        self.assertEqual(receipt.request_path, "/pricing-protected")

        response = self.api_client.get("/api/integrations/x402/receipts/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["nonce"], nonce)
