# payments/views.py

from decimal import Decimal
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from algorand.utils import perform_swap_algo_to_usdc
from payments.utils import calculate_fees, generate_algo_payment_qr
from .models import Transaction
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
        data["user"] = request.user.id
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        transaction = serializer.save()

        # Ici on pourrait appeler un service pour générer un QR code de paiement Algorand, ou vérifier le wallet de l’utilisateur
        return Response({"message": "Transaction created.", "tx_id": transaction.id}, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([AllowAny])  # à sécuriser plus tard
def algo_payment_webhook(request):
    tx_id = request.data.get("tx_id")

    try:
        tx = Transaction.objects.get(algo_tx_id=tx_id, status="pending")
        # Ici on simule une confirmation
        tx.status = "confirmed"
        tx.confirmed_at = timezone.now()
        tx.notes = "Confirmed via webhook"
        tx.save()

        # Lancer le swap ALGO → USDC
        usdc_amount = perform_swap_algo_to_usdc(tx.amount)
        tx.usdc_received = usdc_amount
        tx.notes += f" | Swapped to USDC: {usdc_amount}"
        tx.save()

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

def create(self, request, *args, **kwargs):
    data = request.data.copy()
    amount = Decimal(data.get("amount"))
    platform_fee, net_amount = calculate_fees(amount)

    data["user"] = request.user.id
    data["platform_fee"] = platform_fee
    data["net_amount"] = net_amount

    serializer = self.get_serializer(data=data)
    serializer.is_valid(raise_exception=True)
    transaction = serializer.save()

    return Response({
        "message": "Transaction created.",
        "transaction_id": transaction.id,
        "amount": str(transaction.amount),
        "platform_fee": str(transaction.platform_fee),
        "net_amount": str(transaction.net_amount)
    }, status=status.HTTP_201_CREATED)