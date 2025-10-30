import uuid
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


class CurrencyChoices(models.TextChoices):
    ALGO = "ALGO", "Algorand"
    USDC = "USDC", "USD Coin (Algorand)"


class PlanInterval(models.TextChoices):
    MONTH = "month", "Monthly"
    YEAR = "year", "Yearly"


class SubscriptionStatus(models.TextChoices):
    INCOMPLETE = "incomplete", "Incomplete"
    TRIALING = "trialing", "Trialing"
    ACTIVE = "active", "Active"
    PAST_DUE = "past_due", "Past Due"
    CANCELED = "canceled", "Canceled"
    INCOMPLETE_EXPIRED = "incomplete_expired", "Incomplete Expired"
    UNPAID = "unpaid", "Unpaid"


class InvoiceStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    OPEN = "open", "Open"
    PAID = "paid", "Paid"
    UNCOLLECTIBLE = "uncollectible", "Uncollectible"
    VOID = "void", "Void"


class PaymentIntentStatus(models.TextChoices):
    REQUIRES_ACTION = "requires_action", "Requires Action"
    PROCESSING = "processing", "Processing"
    SUCCEEDED = "succeeded", "Succeeded"
    FAILED = "failed", "Failed"


class CouponDuration(models.TextChoices):
    ONCE = "once", "Once"
    REPEATING = "repeating", "Repeating"
    FOREVER = "forever", "Forever"


class CheckoutSessionStatus(models.TextChoices):
    OPEN = "open", "Open"
    COMPLETED = "completed", "Completed"
    EXPIRED = "expired", "Expired"


class Plan(models.Model):
    code = models.SlugField(max_length=64, unique=True)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=6)
    currency = models.CharField(max_length=10, choices=CurrencyChoices.choices, default=CurrencyChoices.ALGO)
    interval = models.CharField(max_length=10, choices=PlanInterval.choices, default=PlanInterval.MONTH)
    trial_days = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="plans",
    )
    contract_app_id = models.PositiveBigIntegerField(null=True, blank=True, help_text="Algorand app ID for on-chain enforcement")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("code",)

    def __str__(self) -> str:
        return f"{self.name} ({self.amount} {self.currency})"


class PlanFeature(models.Model):
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name="features")
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("sort_order", "id")

    def __str__(self) -> str:
        return f"{self.plan.code}: {self.name}"


class PriceTier(models.Model):
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name="price_tiers")
    up_to = models.PositiveIntegerField(null=True, blank=True, help_text="Upper bound of this tier (inclusive).")
    unit_amount = models.DecimalField(max_digits=12, decimal_places=6)
    currency = models.CharField(max_length=10, choices=CurrencyChoices.choices, default=CurrencyChoices.ALGO)

    class Meta:
        ordering = ("plan", "up_to")
        constraints = [
            models.UniqueConstraint(fields=("plan", "up_to"), name="unique_plan_tier"),
        ]

    def __str__(self) -> str:
        label = f"{self.up_to}" if self.up_to is not None else "∞"
        return f"{self.plan.code} tier ≤ {label}"


class Coupon(models.Model):
    code = models.CharField(max_length=40, unique=True)
    name = models.CharField(max_length=120, blank=True)
    duration = models.CharField(max_length=10, choices=CouponDuration.choices, default=CouponDuration.ONCE)
    duration_in_months = models.PositiveIntegerField(null=True, blank=True)
    percent_off = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    amount_off = models.DecimalField(max_digits=12, decimal_places=6, null=True, blank=True)
    currency = models.CharField(max_length=10, choices=CurrencyChoices.choices, default=CurrencyChoices.ALGO)
    max_redemptions = models.PositiveIntegerField(null=True, blank=True)
    redeem_by = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def is_percentage(self) -> bool:
        return self.percent_off is not None

    def __str__(self) -> str:
        return self.code


class Subscription(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="subscriptions")
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="subscriptions")
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True, related_name="subscriptions")
    status = models.CharField(max_length=24, choices=SubscriptionStatus.choices, default=SubscriptionStatus.TRIALING)
    wallet_address = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField(default=1)
    trial_end_at = models.DateTimeField(null=True, blank=True)
    current_period_start = models.DateTimeField(default=timezone.now)
    current_period_end = models.DateTimeField(null=True, blank=True)
    cancel_at_period_end = models.BooleanField(default=False)
    canceled_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("status", "current_period_end")),
        ]

    def __str__(self) -> str:
        return f"{self.user.email} / {self.plan.code}"

    @property
    def is_active(self) -> bool:
        return self.status in {SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING}


class Invoice(models.Model):
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name="invoices")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="invoices")
    number = models.CharField(max_length=40, unique=True)
    status = models.CharField(max_length=20, choices=InvoiceStatus.choices, default=InvoiceStatus.DRAFT)
    currency = models.CharField(max_length=10, choices=CurrencyChoices.choices)
    subtotal = models.DecimalField(max_digits=12, decimal_places=6, default=Decimal("0"))
    discount_total = models.DecimalField(max_digits=12, decimal_places=6, default=Decimal("0"))
    tax_total = models.DecimalField(max_digits=12, decimal_places=6, default=Decimal("0"))
    total = models.DecimalField(max_digits=12, decimal_places=6, default=Decimal("0"))
    platform_fee = models.DecimalField(max_digits=12, decimal_places=6, default=Decimal("0"))
    period_start = models.DateTimeField(null=True, blank=True)
    period_end = models.DateTimeField(null=True, blank=True)
    due_at = models.DateTimeField(null=True, blank=True)
    issued_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    memo = models.TextField(blank=True)

    class Meta:
        ordering = ("-issued_at",)
        indexes = [
            models.Index(fields=("status", "due_at")),
        ]

    def __str__(self) -> str:
        return self.number


class InvoiceLineItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="line_items")
    plan = models.ForeignKey(Plan, on_delete=models.SET_NULL, null=True, blank=True, related_name="invoice_line_items")
    description = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField(default=1)
    unit_amount = models.DecimalField(max_digits=12, decimal_places=6)
    total_amount = models.DecimalField(max_digits=12, decimal_places=6)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ("invoice", "id")

    def __str__(self) -> str:
        return f"{self.invoice.number}: {self.description}"


class PaymentIntent(models.Model):
    invoice = models.OneToOneField(Invoice, on_delete=models.CASCADE, related_name="payment_intent")
    status = models.CharField(max_length=20, choices=PaymentIntentStatus.choices, default=PaymentIntentStatus.REQUIRES_ACTION)
    amount = models.DecimalField(max_digits=12, decimal_places=6)
    currency = models.CharField(max_length=10, choices=CurrencyChoices.choices)
    algo_tx_id = models.CharField(max_length=128, blank=True)
    swap_tx_ids = models.JSONField(default=list, blank=True)
    confirmed_round = models.PositiveIntegerField(null=True, blank=True)
    usdc_received = models.DecimalField(max_digits=12, decimal_places=6, null=True, blank=True)
    attempts = models.PositiveIntegerField(default=0)
    last_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"PI-{self.invoice.number}"


class EventLog(models.Model):
    event_type = models.CharField(max_length=80)
    resource_type = models.CharField(max_length=80)
    resource_id = models.CharField(max_length=64)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("event_type", "created_at")),
        ]

    def __str__(self) -> str:
        return f"{self.event_type} @ {self.created_at.isoformat()}"


class CheckoutSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="checkout_sessions")
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name="checkout_sessions")
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True, related_name="checkout_sessions")
    wallet_address = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=12, choices=CheckoutSessionStatus.choices, default=CheckoutSessionStatus.OPEN)
    success_url = models.URLField(blank=True)
    cancel_url = models.URLField(blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("status", "expires_at")),
        ]

    def save(self, *args, **kwargs):
        if self.expires_at is None:
            self.expires_at = timezone.now() + timedelta(minutes=30)
        super().save(*args, **kwargs)

    @property
    def is_expired(self) -> bool:
        return self.expires_at is not None and timezone.now() >= self.expires_at

    def __str__(self) -> str:
        return f"CheckoutSession {self.id} for {self.plan.code}"
