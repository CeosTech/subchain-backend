from rest_framework import serializers

from .models import (
    Coupon,
    CheckoutSession,
    EventLog,
    Invoice,
    InvoiceLineItem,
    PaymentIntent,
    Plan,
    PlanFeature,
    PriceTier,
    Subscription,
    SubscriptionStatus,
)


class PlanFeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlanFeature
        fields = ("id", "name", "description", "sort_order")


class PriceTierSerializer(serializers.ModelSerializer):
    class Meta:
        model = PriceTier
        fields = ("id", "up_to", "unit_amount", "currency")


class PlanSerializer(serializers.ModelSerializer):
    features = PlanFeatureSerializer(many=True, read_only=True)
    price_tiers = PriceTierSerializer(many=True, read_only=True)

    class Meta:
        model = Plan
        fields = (
            "id",
            "code",
            "name",
            "description",
            "amount",
            "currency",
            "interval",
            "trial_days",
            "is_active",
            "metadata",
            "features",
            "price_tiers",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("created_at", "updated_at")


class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = "__all__"
        read_only_fields = ("created_at", "updated_at")


class SubscriptionSerializer(serializers.ModelSerializer):
    plan = PlanSerializer(read_only=True)
    plan_id = serializers.PrimaryKeyRelatedField(source="plan", queryset=Plan.objects.all(), write_only=True)
    coupon = CouponSerializer(read_only=True)
    coupon_id = serializers.PrimaryKeyRelatedField(
        source="coupon", queryset=Coupon.objects.all(), write_only=True, required=False, allow_null=True
    )

    class Meta:
        model = Subscription
        fields = (
            "id",
            "user",
            "plan",
            "plan_id",
            "coupon",
            "coupon_id",
            "status",
            "wallet_address",
            "quantity",
            "trial_end_at",
            "current_period_start",
            "current_period_end",
            "cancel_at_period_end",
            "canceled_at",
            "ended_at",
            "metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "user",
            "status",
            "trial_end_at",
            "current_period_start",
            "current_period_end",
            "cancel_at_period_end",
            "canceled_at",
            "ended_at",
            "created_at",
            "updated_at",
        )
        extra_kwargs = {
            "wallet_address": {"required": True},
            "quantity": {"min_value": 1, "default": 1},
            "metadata": {"default": dict},
        }

    status = serializers.CharField(read_only=True, default=SubscriptionStatus.TRIALING)


class InvoiceLineItemSerializer(serializers.ModelSerializer):
    plan = PlanSerializer(read_only=True)
    plan_id = serializers.PrimaryKeyRelatedField(
        source="plan", queryset=Plan.objects.all(), write_only=True, required=False, allow_null=True
    )

    class Meta:
        model = InvoiceLineItem
        fields = (
            "id",
            "plan",
            "plan_id",
            "description",
            "quantity",
            "unit_amount",
            "total_amount",
            "metadata",
        )


class PaymentIntentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentIntent
        fields = "__all__"
        read_only_fields = ("created_at", "updated_at")


class InvoiceSerializer(serializers.ModelSerializer):
    subscription = SubscriptionSerializer(read_only=True)
    subscription_id = serializers.PrimaryKeyRelatedField(
        source="subscription", queryset=Subscription.objects.all(), write_only=True
    )
    line_items = InvoiceLineItemSerializer(many=True, required=False)
    payment_intent = PaymentIntentSerializer(read_only=True)

    class Meta:
        model = Invoice
        fields = (
            "id",
            "subscription",
            "subscription_id",
            "user",
            "number",
            "status",
            "currency",
            "subtotal",
            "discount_total",
            "tax_total",
            "total",
            "platform_fee",
            "period_start",
            "period_end",
            "due_at",
            "issued_at",
            "paid_at",
            "metadata",
            "memo",
            "line_items",
            "payment_intent",
        )
        read_only_fields = ("issued_at", "paid_at")

    def create(self, validated_data):
        line_items_data = validated_data.pop("line_items", [])
        invoice = super().create(validated_data)
        for item_data in line_items_data:
            InvoiceLineItem.objects.create(invoice=invoice, **item_data)
        return invoice

    def update(self, instance, validated_data):
        line_items_data = validated_data.pop("line_items", None)
        invoice = super().update(instance, validated_data)
        if line_items_data is not None:
            invoice.line_items.all().delete()
            for item_data in line_items_data:
                InvoiceLineItem.objects.create(invoice=invoice, **item_data)
        return invoice


class EventLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventLog
        fields = "__all__"


class CheckoutSessionSerializer(serializers.ModelSerializer):
    plan = PlanSerializer(read_only=True)
    plan_id = serializers.PrimaryKeyRelatedField(source="plan", queryset=Plan.objects.all(), write_only=True)
    coupon = CouponSerializer(read_only=True)
    coupon_id = serializers.PrimaryKeyRelatedField(
        source="coupon", queryset=Coupon.objects.all(), write_only=True, required=False, allow_null=True
    )

    class Meta:
        model = CheckoutSession
        fields = (
            "id",
            "user",
            "plan",
            "plan_id",
            "coupon",
            "coupon_id",
            "wallet_address",
            "quantity",
            "status",
            "success_url",
            "cancel_url",
            "expires_at",
            "metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "user", "status", "expires_at", "created_at", "updated_at")
        extra_kwargs = {
            "wallet_address": {"required": True},
            "quantity": {"min_value": 1, "default": 1},
            "metadata": {"default": dict},
        }
