# integrations/serializers.py

from decimal import Decimal, InvalidOperation

from rest_framework import serializers

from .models import (
    CreditSubscription,
    CreditUsage,
    EndpointPricingRule,
    Integration,
    PaymentLink,
    PaymentLinkEvent,
    PaymentLinkType,
    PaymentReceipt,
    X402CreditPlan,
)

class IntegrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Integration
        fields = "__all__"
        read_only_fields = [
            "id",
            "user",
            "created_at",
            "updated_at",
            "status",
            "last_success_at",
            "last_error_at",
            "failure_count",
            "last_error_message",
        ]


class EndpointPricingRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = EndpointPricingRule
        fields = [
            "id",
            "pattern",
            "methods",
            "amount",
            "currency",
            "network",
            "priority",
            "is_active",
            "description",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_amount(self, value: Decimal) -> Decimal:
        if value <= Decimal("0"):
            raise serializers.ValidationError("Amount must be greater than zero.")
        return value

    def validate_methods(self, value):
        if value in (None, ""):
            return []
        if not isinstance(value, (list, tuple)):
            raise serializers.ValidationError("Methods must be a list of HTTP verbs.")
        cleaned = []
        for method in value:
            method_str = str(method).strip().upper()
            if not method_str:
                continue
            if method_str not in {"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"}:
                raise serializers.ValidationError(f"Unsupported HTTP method '{method}'.")
            if method_str not in cleaned:
                cleaned.append(method_str)
        return cleaned


class PaymentReceiptSerializer(serializers.ModelSerializer):
    amount = serializers.SerializerMethodField()

    class Meta:
        model = PaymentReceipt
        fields = [
            "id",
            "nonce",
            "status",
            "amount",
            "currency",
            "network",
            "payer_address",
            "request_path",
            "request_method",
            "metadata",
            "verified_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_amount(self, obj: PaymentReceipt) -> str:
        try:
            return f"{obj.amount:.8f}".rstrip("0").rstrip(".")
        except (InvalidOperation, AttributeError):
            return str(obj.amount)


class PaymentLinkEventSerializer(serializers.ModelSerializer):
    amount = serializers.SerializerMethodField()
    fee_amount = serializers.SerializerMethodField()
    merchant_amount = serializers.SerializerMethodField()

    class Meta:
        model = PaymentLinkEvent
        fields = [
            "id",
            "payer_address",
            "amount",
            "fee_amount",
            "merchant_amount",
            "metadata",
            "created_at",
        ]
        read_only_fields = fields

    def get_amount(self, obj: PaymentLinkEvent) -> str:
        try:
            return f"{obj.amount:.8f}".rstrip("0").rstrip(".")
        except (InvalidOperation, AttributeError):
            return str(obj.amount)

    def get_fee_amount(self, obj: PaymentLinkEvent) -> str:
        try:
            return f"{obj.fee_amount:.8f}".rstrip("0").rstrip(".")
        except (InvalidOperation, AttributeError):
            return str(obj.fee_amount)

    def get_merchant_amount(self, obj: PaymentLinkEvent) -> str:
        try:
            return f"{obj.merchant_amount:.8f}".rstrip("0").rstrip(".")
        except (InvalidOperation, AttributeError):
            return str(obj.merchant_amount)


class _BasePaymentLinkSerializer(serializers.ModelSerializer):
    events = PaymentLinkEventSerializer(many=True, read_only=True)

    class Meta:
        model = PaymentLink
        fields = [
            "id",
            "kind",
            "name",
            "slug",
            "description",
            "amount",
            "currency",
            "network",
            "success_url",
            "callback_url",
            "pay_to_address",
            "platform_fee_percent",
            "is_active",
            "metadata",
            "pattern",
            "created_at",
            "updated_at",
            "events",
        ]
        read_only_fields = ["id", "pattern", "created_at", "updated_at", "events", "kind"]
        extra_kwargs = {"slug": {"required": False, "allow_blank": True}}

    default_kind = PaymentLinkType.LINK

    def validate_amount(self, value: Decimal) -> Decimal:
        if value <= Decimal("0"):
            raise serializers.ValidationError("Amount must be greater than zero.")
        return value

    def validate_platform_fee_percent(self, value: Decimal) -> Decimal:
        if value < Decimal("0") or value > Decimal("100"):
            raise serializers.ValidationError("platform_fee_percent must be between 0 and 100.")
        return value

    def validate(self, attrs):
        attrs["kind"] = self.default_kind
        return super().validate(attrs)

    def create(self, validated_data):
        validated_data["kind"] = self.default_kind
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data["kind"] = instance.kind  # immutable once created
        return super().update(instance, validated_data)


class PaymentLinkSerializer(_BasePaymentLinkSerializer):
    default_kind = PaymentLinkType.LINK


class PaymentWidgetSerializer(_BasePaymentLinkSerializer):
    default_kind = PaymentLinkType.WIDGET


class CreditPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = X402CreditPlan
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "amount",
            "currency",
            "network",
            "credits_per_payment",
            "auto_renew",
            "is_active",
            "metadata",
            "pay_to_address",
            "platform_fee_percent",
            "pattern",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "slug", "pattern", "created_at", "updated_at"]
        extra_kwargs = {"slug": {"required": False, "allow_blank": True}}

    def validate_amount(self, value: Decimal) -> Decimal:
        if value <= Decimal("0"):
            raise serializers.ValidationError("Amount must be greater than zero.")
        return value

    def validate_credits_per_payment(self, value: int) -> int:
        if value <= 0:
            raise serializers.ValidationError("credits_per_payment must be positive.")
        return value

    def validate_platform_fee_percent(self, value: Decimal) -> Decimal:
        if value < Decimal("0") or value > Decimal("100"):
            raise serializers.ValidationError("platform_fee_percent must be between 0 and 100.")
        return value


class CreditSubscriptionSerializer(serializers.ModelSerializer):
    plan = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = CreditSubscription
        fields = [
            "id",
            "plan",
            "consumer_ref",
            "credits_remaining",
            "total_credits",
            "last_purchase_at",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class CreditUsageSerializer(serializers.ModelSerializer):
    subscription = serializers.PrimaryKeyRelatedField(read_only=True)
    fee_amount = serializers.SerializerMethodField()
    merchant_amount = serializers.SerializerMethodField()

    class Meta:
        model = CreditUsage
        fields = [
            "id",
            "subscription",
            "usage_type",
            "credits_delta",
            "description",
            "fee_amount",
            "merchant_amount",
            "metadata",
            "created_at",
        ]
        read_only_fields = fields

    def get_fee_amount(self, obj: CreditUsage) -> str:
        try:
            return f"{obj.fee_amount:.8f}".rstrip("0").rstrip(".")
        except (InvalidOperation, AttributeError):
            return str(obj.fee_amount)

    def get_merchant_amount(self, obj: CreditUsage) -> str:
        try:
            return f"{obj.merchant_amount:.8f}".rstrip("0").rstrip(".")
        except (InvalidOperation, AttributeError):
            return str(obj.merchant_amount)
