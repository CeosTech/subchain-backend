# payments/serializers.py

from rest_framework import serializers
from .models import Transaction

class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = "__all__"
        read_only_fields = ("status", "created_at", "confirmed_at", "usdc_received", "algo_tx_id", "notes")
