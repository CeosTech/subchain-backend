from rest_framework import serializers


class PaymentWebhookSerializer(serializers.Serializer):
    transaction_id = serializers.CharField()
