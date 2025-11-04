from __future__ import annotations

import logging

from django.http import JsonResponse

from .. import x402


logger = logging.getLogger(__name__)


class X402PaymentMiddleware:
    """
    Enforces x402 payment requirements on protected endpoints.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        price = x402.match_price(request.path, request.method, request)
        if price is None:
            return self.get_response(request)

        receipt = request.headers.get("X-402-Receipt")
        if receipt:
            verification = x402.verify_receipt(receipt, price, request)
            if verification:
                x402.attach_payment_metadata(request, verification)
                logger.debug(
                    "x402 payment accepted path=%s method=%s price=%s",
                    request.path,
                    request.method,
                    price,
                )
                return self.get_response(request)

        challenge_headers = x402.build_challenge(request, price)
        response = JsonResponse({"detail": "Payment required"}, status=402)
        for header, value in challenge_headers.items():
            if value:
                response[header] = value
        return response
