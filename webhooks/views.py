# webhooks/views.py
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from payments.models import Transaction
from algorand.utils import perform_swap_algo_to_usdc
from .models import WebhookLog

@api_view(['POST'])
def payment_webhook(request):
    payload = request.data

    # Log initial
    log = WebhookLog.objects.create(endpoint="payments", payload=payload)

    tx_id = payload.get("transaction_id")
    try:
        tx = Transaction.objects.get(id=tx_id, currency="ALGO", status="confirmed")

        result = perform_swap_algo_to_usdc(
            sender_address=tx.sender_address,
            sender_private_key="YOUR_PRIVATE_KEY_HERE",  # ⚠️ À remplacer par gestion sécurisée
            amount_algo=int(tx.amount * 1_000_000),
            transaction_id=tx.id
        )

        tx.swap_status = result["status"]
        tx.swap_info = result
        tx.save()

        log.success = result["status"] == "success"
        log.response = result
        log.save()

        return Response({"detail": "Swap processed."}, status=status.HTTP_200_OK)

    except Transaction.DoesNotExist:
        log.success = False
        log.response = {"error": "Transaction not found or not eligible."}
        log.save()
        return Response({"error": "Transaction not found."}, status=status.HTTP_404_NOT_FOUND)
