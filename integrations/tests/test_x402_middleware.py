from __future__ import annotations

import json

from django.http import JsonResponse
from django.test import TestCase, override_settings
from django.urls import path


def protected_view(request):
    payload = {"ok": True}
    if hasattr(request, "x402_payment"):
        payload["payment"] = request.x402_payment
    return JsonResponse(payload)


urlpatterns = [
    path("protected/", protected_view),
]


def fake_verifier(receipt: str, price, request):
    if not receipt:
        return None
    return {
        "nonce": receipt,
        "amount": str(price),
        "payer": "test-wallet",
    }


@override_settings(
    ROOT_URLCONF=__name__,
    X402_ENABLED=True,
    X402_PAYTO_ADDRESS="TEST_WALLET",
    X402_DEFAULT_PRICE="0",
    X402_PRICING_RULES=json.dumps({"/protected": {"amount": "0.25", "methods": ["GET"]}}),
    X402_RECEIPT_VERIFIER="integrations.tests.test_x402_middleware.fake_verifier",
    X402_NONCE_TTL_SECONDS=60,
)
class X402MiddlewareTests(TestCase):
    def test_requires_payment_when_receipt_missing(self):
        response = self.client.get("/protected/")

        self.assertEqual(response.status_code, 402)
        self.assertEqual(response.json(), {"detail": "Payment required"})
        self.assertEqual(response["X-402-PayTo"], "TEST_WALLET")
        self.assertEqual(response["X-402-Amount"], "0.25")
        self.assertTrue(response["X-402-Nonce"])
        self.assertEqual(response["X-402-Currency"], "USDC")
        self.assertEqual(response["X-402-Network"], "algorand")

    def test_allows_request_with_valid_receipt(self):
        challenge = self.client.get("/protected/")
        nonce = challenge["X-402-Nonce"]

        response = self.client.get("/protected/", HTTP_X_402_RECEIPT=nonce)

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertIn("payment", payload)
        self.assertEqual(payload["payment"]["nonce"], nonce)

    def test_rejects_replayed_nonce(self):
        challenge = self.client.get("/protected/")
        nonce = challenge["X-402-Nonce"]

        first = self.client.get("/protected/", HTTP_X_402_RECEIPT=nonce)
        self.assertEqual(first.status_code, 200)

        replay = self.client.get("/protected/", HTTP_X_402_RECEIPT=nonce)
        self.assertEqual(replay.status_code, 402)
