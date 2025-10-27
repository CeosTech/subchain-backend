# payments/views.py

from decimal import Decimal, InvalidOperation
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from payments.utils import calculate_fees, generate_algo_payment_qr
from .models import Transaction, TransactionStatus
from .serializers import TransactionSerializer
from django.utils import timezone

class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        amount_raw = data.get("amount")
        try:
            amount = Decimal(str(amount_raw))
        except (InvalidOperation, TypeError):
            return Response({"error": "Invalid amount."}, status=status.HTTP_400_BAD_REQUEST)

        platform_fee, net_amount = calculate_fees(amount)
        data["user"] = request.user.id
        data["platform_fee"] = platform_fee
        data["net_amount"] = net_amount

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        transaction = serializer.save()

        headers = self.get_success_headers(serializer.data)
        return Response(
            {
                "message": "Transaction created.",
                "transaction_id": transaction.id,
                "amount": str(transaction.amount),
                "platform_fee": str(transaction.platform_fee),
                "net_amount": str(transaction.net_amount),
            },
            status=status.HTTP_201_CREATED,
            headers=headers,
        )


@api_view(["POST"])
@permission_classes([AllowAny])  # à sécuriser plus tard
def algo_payment_webhook(request):
    tx_id = request.data.get("tx_id")

    try:
        tx = Transaction.objects.get(algo_tx_id=tx_id, status=TransactionStatus.PENDING)
        # Ici on simule une confirmation
        tx.confirmed_at = timezone.now()
        tx.notes = "Confirmed via webhook"
        tx.save(update_fields=["confirmed_at", "notes"])

        from .services import SwapExecutionError, execute_algo_to_usdc_swap

        try:
            execute_algo_to_usdc_swap(tx)
        except SwapExecutionError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        return Response({"message": "Transaction confirmed and swapped."})
    except Transaction.DoesNotExist:
        return Response({"error": "Transaction not found."}, status=404)
    

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_algo_qr(request):
    wallet = request.user.wallet_address
    amount = request.GET.get("amount", "1.0")
    qr_base64 = generate_algo_payment_qr(wallet, float(amount))
    return Response({"qr_code_base64": qr_base64})
