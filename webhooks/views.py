# webhooks/views.py
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone

from payments.models import Transaction, CurrencyChoices, TransactionStatus
from .models import WebhookLog

@api_view(['POST'])
def payment_webhook(request):
    payload = request.data

    # Log initial
    log = WebhookLog.objects.create(endpoint="payments", payload=payload)

    tx_id = payload.get("transaction_id")
    try:
        tx = Transaction.objects.get(id=tx_id, currency=CurrencyChoices.ALGO)

        if tx.status != TransactionStatus.CONFIRMED:
            tx.status = TransactionStatus.CONFIRMED
            tx.confirmed_at = timezone.now()
            tx.notes = "Confirmed via webhook"
            tx.save(update_fields=["status", "confirmed_at", "notes"])

        from payments.services import SwapExecutionError, execute_algo_to_usdc_swap

        try:
            result = execute_algo_to_usdc_swap(tx)
        except SwapExecutionError as exc:
            log.success = False
            log.response = {"error": str(exc)}
            log.save()
            return Response({"error": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        log.success = result.get("status") == "success"
        log.response = result
        log.save()

        if not log.success:
            return Response({"error": "Swap failed."}, status=status.HTTP_502_BAD_GATEWAY)

        return Response({"detail": "Swap processed."}, status=status.HTTP_200_OK)

    except Transaction.DoesNotExist:
        log.success = False
        log.response = {"error": "Transaction not found or not eligible."}
        log.save()
        return Response({"error": "Transaction not found."}, status=status.HTTP_404_NOT_FOUND)
