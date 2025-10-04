# currency/serializers.py

from rest_framework import serializers
from .models import Currency, ExchangeRate

class CurrencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Currency
        fields = '__all__'

class ExchangeRateSerializer(serializers.ModelSerializer):
    base_currency = CurrencySerializer(read_only=True)
    target_currency = CurrencySerializer(read_only=True)

    class Meta:
        model = ExchangeRate
        fields = '__all__'
