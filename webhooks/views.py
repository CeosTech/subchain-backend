# webhooks/views.py
import hmac
from hmac import new as hmac_new
from hashlib import sha256

from django.conf import settings
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from payments.models import Transaction, CurrencyChoices, TransactionStatus
from .models import WebhookLog
from .serializers import PaymentWebhookSerializer
from .tasks import process_payment_webhook


def _verify_signature(request):
    secret = getattr(settings, "WEBHOOK_SECRET", None)
    if not secret:
        return True

    signature = request.headers.get("X-Signature")
    if not signature:
        return False

    body = request.body
    computed = hmac_new(secret.encode(), body, sha256).hexdigest()
    return hmac.compare_digest(signature, computed)

@api_view(['POST'])
def payment_webhook(request):
    if not _verify_signature(request):
        return Response({"error": "Invalid signature"}, status=status.HTTP_401_UNAUTHORIZED)

    serializer = PaymentWebhookSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    payload = serializer.validated_data

    # Log initial
    external_id = f"{payload['transaction_id']}"
    log, created = WebhookLog.objects.get_or_create(
        endpoint="payments",
        external_id=external_id,
        defaults={
            "payload": payload,
            "headers": dict(request.headers),
        },
    )
    if not created and log.success:
        return Response({"detail": "Duplicate webhook ignored."}, status=status.HTTP_200_OK)

    process_payment_webhook.delay(log.id, payload["transaction_id"])
    return Response({"detail": "Webhook received."}, status=status.HTTP_202_ACCEPTED)
