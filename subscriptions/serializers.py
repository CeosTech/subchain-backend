from rest_framework import serializers

from .models import (
    Coupon,
    CouponDuration,
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
    CustomerType,
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
            "created_by",
            "features",
            "price_tiers",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("created_at", "updated_at", "created_by")


class CouponSerializer(serializers.ModelSerializer):
    created_by = serializers.ReadOnlyField(source="created_by_id")

    class Meta:
        model = Coupon
        fields = "__all__"
        read_only_fields = ("created_at", "updated_at", "created_by")

    def validate_code(self, value: str) -> str:
        return value.strip().upper()

    def validate(self, attrs):
        percent_off = attrs.get("percent_off", getattr(self.instance, "percent_off", None))
        amount_off = attrs.get("amount_off", getattr(self.instance, "amount_off", None))
        duration = attrs.get("duration", getattr(self.instance, "duration", None))
        duration_in_months = attrs.get(
            "duration_in_months", getattr(self.instance, "duration_in_months", None)
        )

        if percent_off and amount_off:
            raise serializers.ValidationError("Use either percent_off or amount_off, not both.")
        if not percent_off and not amount_off:
            raise serializers.ValidationError("Specify percent_off or amount_off for the coupon.")

        if duration == CouponDuration.REPEATING and not duration_in_months:
            raise serializers.ValidationError("duration_in_months is required when duration is repeating.")

        if percent_off is not None:
            if percent_off <= 0 or percent_off > 100:
                raise serializers.ValidationError({"percent_off": "Provide a percentage between 0 and 100."})

        if amount_off is not None and amount_off <= 0:
            raise serializers.ValidationError({"amount_off": "Amount off must be greater than zero."})

        max_redemptions = attrs.get("max_redemptions")
        if max_redemptions is not None and max_redemptions <= 0:
            raise serializers.ValidationError("max_redemptions must be greater than zero.")

        return attrs


class SubscriptionSerializer(serializers.ModelSerializer):
    plan = PlanSerializer(read_only=True)
    plan_id = serializers.PrimaryKeyRelatedField(source="plan", queryset=Plan.objects.all(), write_only=True)
    coupon = CouponSerializer(read_only=True)
    coupon_id = serializers.PrimaryKeyRelatedField(
        source="coupon", queryset=Coupon.objects.all(), write_only=True, required=False, allow_null=True
    )
    coupon_code = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Subscription
        fields = (
            "id",
            "user",
            "plan",
            "plan_id",
            "coupon",
            "coupon_id",
            "coupon_code",
            "status",
            "wallet_address",
            "quantity",
            "customer_type",
            "company_name",
            "vat_number",
            "billing_email",
            "billing_phone",
            "billing_address",
            "billing_same_as_shipping",
            "shipping_address",
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
            "billing_same_as_shipping": {"default": True},
        }

    status = serializers.CharField(read_only=True, default=SubscriptionStatus.TRIALING)

    def validate(self, attrs):
        request = self.context.get("request")
        coupon = attrs.get("coupon")
        coupon_code = attrs.pop("coupon_code", None)
        instance = getattr(self, "instance", None)

        if coupon and coupon_code:
            raise serializers.ValidationError("Provide coupon by id or code, not both.")

        if coupon_code:
            try:
                coupon = Coupon.objects.get(code__iexact=coupon_code.strip())
            except Coupon.DoesNotExist:
                raise serializers.ValidationError({"coupon_code": "Coupon not found."})
            attrs["coupon"] = coupon

        user = getattr(request, "user", None)
        if coupon:
            self._validate_coupon_access(user, coupon)

        customer_type = attrs.get(
            "customer_type",
            getattr(instance, "customer_type", CustomerType.INDIVIDUAL),
        )
        if customer_type == CustomerType.BUSINESS:
            company_name = attrs.get("company_name", getattr(instance, "company_name", ""))
            vat_number = attrs.get("vat_number", getattr(instance, "vat_number", ""))
            if not company_name:
                raise serializers.ValidationError({"company_name": "Company name is required for businesses."})
            if not vat_number:
                raise serializers.ValidationError({"vat_number": "VAT number is required for businesses."})

        billing_email = attrs.get("billing_email", getattr(instance, "billing_email", ""))
        if not billing_email:
            raise serializers.ValidationError({"billing_email": "Billing email is required."})

        billing_address = attrs.get("billing_address", getattr(instance, "billing_address", ""))
        if not billing_address:
            raise serializers.ValidationError({"billing_address": "Billing address is required."})

        billing_same_as_shipping = attrs.get(
            "billing_same_as_shipping",
            getattr(instance, "billing_same_as_shipping", True),
        )
        shipping_address = attrs.get("shipping_address", getattr(instance, "shipping_address", ""))
        if not billing_same_as_shipping and not shipping_address:
            raise serializers.ValidationError(
                {"shipping_address": "Provide a shipping address when it differs from billing."}
            )

        return attrs

    @staticmethod
    def _validate_coupon_access(user, coupon: Coupon) -> None:
        if user is None or not getattr(user, "is_authenticated", False) or user.is_staff:
            return
        if coupon.created_by and coupon.created_by != user:
            raise serializers.ValidationError({"coupon": "You cannot use this coupon."})

    def update(self, instance, validated_data):
        billing_same = validated_data.get("billing_same_as_shipping", instance.billing_same_as_shipping)
        if billing_same:
            validated_data["shipping_address"] = ""
        return super().update(instance, validated_data)


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
    coupon_code = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = CheckoutSession
        fields = (
            "id",
            "user",
            "plan",
            "plan_id",
            "coupon",
            "coupon_id",
            "coupon_code",
            "wallet_address",
            "quantity",
            "customer_type",
            "company_name",
            "vat_number",
            "billing_email",
            "billing_phone",
            "billing_address",
            "billing_same_as_shipping",
            "shipping_address",
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
            "billing_same_as_shipping": {"default": True},
        }

    def validate(self, attrs):
        request = self.context.get("request")
        coupon = attrs.get("coupon")
        coupon_code = attrs.pop("coupon_code", None)
        instance = getattr(self, "instance", None)

        if coupon and coupon_code:
            raise serializers.ValidationError("Provide coupon by id or code, not both.")

        if coupon_code:
            try:
                coupon = Coupon.objects.get(code__iexact=coupon_code.strip())
            except Coupon.DoesNotExist:
                raise serializers.ValidationError({"coupon_code": "Coupon not found."})
            attrs["coupon"] = coupon

        user = getattr(request, "user", None)
        if coupon:
            SubscriptionSerializer._validate_coupon_access(user, coupon)

        customer_type = attrs.get("customer_type", getattr(instance, "customer_type", CustomerType.INDIVIDUAL))
        if customer_type == CustomerType.BUSINESS:
            if not attrs.get("company_name", getattr(instance, "company_name", "")):
                raise serializers.ValidationError({"company_name": "Company name is required for businesses."})
            if not attrs.get("vat_number", getattr(instance, "vat_number", "")):
                raise serializers.ValidationError({"vat_number": "VAT number is required for businesses."})

        billing_email = attrs.get("billing_email", getattr(instance, "billing_email", ""))
        if not billing_email:
            raise serializers.ValidationError({"billing_email": "Billing email is required."})

        billing_address = attrs.get("billing_address", getattr(instance, "billing_address", ""))
        if not billing_address:
            raise serializers.ValidationError({"billing_address": "Billing address is required."})

        billing_same_as_shipping = attrs.get(
            "billing_same_as_shipping",
            getattr(instance, "billing_same_as_shipping", True),
        )
        if not billing_same_as_shipping and not attrs.get("shipping_address", getattr(instance, "shipping_address", "")):
            raise serializers.ValidationError(
                {"shipping_address": "Provide a shipping address when it differs from billing."}
            )

        return attrs

    def create(self, validated_data):
        if validated_data.get("billing_same_as_shipping", True):
            validated_data["shipping_address"] = ""
        return super().create(validated_data)

    def update(self, instance, validated_data):
        billing_same = validated_data.get("billing_same_as_shipping", instance.billing_same_as_shipping)
        if billing_same:
            validated_data["shipping_address"] = ""
        return super().update(instance, validated_data)
