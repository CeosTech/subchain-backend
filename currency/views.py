# currency/views.py

from rest_framework import viewsets

from algorand.utils import get_algo_to_usdc_rate
from .models import Currency, ExchangeRate
from .serializers import CurrencySerializer, ExchangeRateSerializer
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

class CurrencyViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Currency.objects.filter(is_active=True)
    serializer_class = CurrencySerializer

class ExchangeRateViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ExchangeRate.objects.all()
    serializer_class = ExchangeRateSerializer


@api_view(['GET'])
def convert_currency(request):
    from_currency = request.GET.get("from")
    to_currency = request.GET.get("to")
    amount = request.GET.get("amount")

    if not all([from_currency, to_currency, amount]):
        return Response({"error": "Missing parameters."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        amount = float(amount)
    except ValueError:
        return Response({"error": "Invalid amount format."}, status=status.HTTP_400_BAD_REQUEST)

    if from_currency == "ALGO" and to_currency == "USDC":
        rate = get_algo_to_usdc_rate()
        converted = round(amount * rate, 6)
        return Response({
            "from": from_currency,
            "to": to_currency,
            "rate": rate,
            "amount": amount,
            "converted_amount": converted
        })

    return Response({"error": "Conversion route not supported yet."}, status=status.HTTP_400_BAD_REQUEST)