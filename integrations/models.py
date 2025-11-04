# integrations/models.py

from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

INTEGRATION_TYPES = [
    ("webhook", "Webhook"),
    ("discord", "Discord"),
    ("slack", "Slack"),
    ("zapier", "Zapier"),
    ("stripe", "Stripe"),
    ("walletconnect", "WalletConnect"),
    ("custom", "Custom"),
]


class IntegrationStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    HEALTHY = "healthy", "Healthy"
    DEGRADED = "degraded", "Degraded"
    FAILED = "failed", "Failed"


class Integration(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="integrations")
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=30, choices=INTEGRATION_TYPES, default="webhook")
    endpoint_url = models.URLField(blank=True)
    auth_token = models.CharField(max_length=255, blank=True)
    config = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=IntegrationStatus.choices, default=IntegrationStatus.PENDING)
    last_success_at = models.DateTimeField(null=True, blank=True)
    last_error_at = models.DateTimeField(null=True, blank=True)
    failure_count = models.PositiveIntegerField(default=0)
    last_error_message = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.type})"

    def mark_success(self):
        self.status = IntegrationStatus.HEALTHY
        self.last_success_at = timezone.now()
        self.failure_count = 0
        self.last_error_message = ""
        self.save(update_fields=["status", "last_success_at", "failure_count", "last_error_message", "updated_at"])

    def mark_failure(self, error_message: str = ""):
        self.failure_count += 1
        self.last_error_at = timezone.now()
        self.last_error_message = error_message[:2000] if error_message else ""
        # escalate status based on failures
        if self.failure_count >= 3:
            self.status = IntegrationStatus.FAILED
        else:
            self.status = IntegrationStatus.DEGRADED
        self.save(update_fields=["status", "failure_count", "last_error_at", "last_error_message", "updated_at"])


class DeliveryStatus(models.TextChoices):
    SUCCESS = "success", "Success"
    FAILED = "failed", "Failed"


class IntegrationDeliveryLog(models.Model):
    integration = models.ForeignKey(Integration, on_delete=models.CASCADE, related_name="deliveries")
    event_type = models.CharField(max_length=120)
    payload = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=10, choices=DeliveryStatus.choices, default=DeliveryStatus.SUCCESS)
    response_code = models.IntegerField(null=True, blank=True)
    response_body = models.TextField(blank=True)
    error_message = models.TextField(blank=True)
    duration_ms = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.integration} → {self.event_type} ({self.status})"


class EndpointPricingRule(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="x402_pricing_rules",
    )
    pattern = models.CharField(max_length=255)
    methods = models.JSONField(default=list, blank=True)
    amount = models.DecimalField(max_digits=20, decimal_places=8)
    currency = models.CharField(max_length=12, default="USDC")
    network = models.CharField(max_length=32, default="algorand")
    priority = models.PositiveIntegerField(default=100)
    is_active = models.BooleanField(default=True)
    description = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("priority", "pattern")
        indexes = [
            models.Index(fields=("user", "priority")),
            models.Index(fields=("user", "pattern")),
        ]
        unique_together = ("user", "pattern")

    def __str__(self):
        return f"{self.pattern} ({self.amount} {self.currency})"

    def normalized_methods(self) -> frozenset[str] | None:
        if not self.methods:
            return None
        iterable = self.methods if isinstance(self.methods, (list, tuple, set)) else [self.methods]
        methods = {str(method).upper() for method in iterable if str(method).strip()}
        return frozenset(methods) if methods else None


class PaymentLinkType(models.TextChoices):
    LINK = "link", "Payment link"
    WIDGET = "widget", "Embedded widget"


class PaymentLink(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payment_links",
    )
    kind = models.CharField(max_length=16, choices=PaymentLinkType.choices, default=PaymentLinkType.LINK)
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=160)
    description = models.TextField(blank=True)
    amount = models.DecimalField(max_digits=20, decimal_places=8)
    currency = models.CharField(max_length=12, default="USDC")
    network = models.CharField(max_length=32, default="algorand")
    pattern = models.CharField(max_length=255, editable=False)
    success_url = models.URLField(blank=True)
    callback_url = models.URLField(blank=True)
    pay_to_address = models.CharField(max_length=128, blank=True)
    platform_fee_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"))
    is_active = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=("user", "slug")),
            models.Index(fields=("user", "kind", "is_active")),
        ]
        unique_together = ("user", "slug")

    def __str__(self):
        return f"{self.name} ({self.kind})"

    @property
    def tenant_prefix(self) -> str:
        return f"/paywall/tenant/{self.user_id}"

    def build_pattern(self) -> str:
        base = "links" if self.kind == PaymentLinkType.LINK else "widgets"
        return f"{self.tenant_prefix}/{base}/{self.slug}"

    def get_paywall_path(self) -> str:
        return self.pattern or self.build_pattern()

    def ensure_slug(self) -> None:
        if self.slug:
            return
        base = slugify(self.name) or "link"
        slug = base
        counter = 1
        while PaymentLink.objects.filter(user=self.user, slug=slug).exclude(pk=self.pk).exists():
            slug = f"{base}-{counter}"
            counter += 1
        self.slug = slug

    def save(self, *args, **kwargs):
        self.ensure_slug()
        self.pattern = self.build_pattern()
        super().save(*args, **kwargs)


class PaymentLinkEvent(models.Model):
    link = models.ForeignKey(PaymentLink, on_delete=models.CASCADE, related_name="events")
    receipt = models.ForeignKey(
        "PaymentReceipt",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="link_events",
    )
    payer_address = models.CharField(max_length=128, blank=True)
    amount = models.DecimalField(max_digits=20, decimal_places=8)
    fee_amount = models.DecimalField(max_digits=20, decimal_places=8, default=Decimal("0"))
    merchant_amount = models.DecimalField(max_digits=20, decimal_places=8, default=Decimal("0"))
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("link", "created_at")),
            models.Index(fields=("payer_address",)),
        ]

    def __str__(self):
        return f"{self.link.name} @ {self.created_at:%Y-%m-%d %H:%M}"


class PaymentReceiptStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    CONFIRMED = "confirmed", "Confirmed"
    REJECTED = "rejected", "Rejected"


class PaymentReceipt(models.Model):
    """
    Stores x402 receipt metadata to prevent replay, support audits, and drive reporting.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="x402_receipts",
        null=True,
        blank=True,
    )
    nonce = models.CharField(max_length=128, unique=True)
    receipt_token = models.TextField(blank=True)
    payer_address = models.CharField(max_length=128, blank=True)
    amount = models.DecimalField(max_digits=20, decimal_places=8)
    currency = models.CharField(max_length=12, default="USDC")
    network = models.CharField(max_length=32, default="algorand")
    status = models.CharField(
        max_length=16,
        choices=PaymentReceiptStatus.choices,
        default=PaymentReceiptStatus.PENDING,
    )
    request_path = models.CharField(max_length=255)
    request_method = models.CharField(max_length=10, default="GET")
    metadata = models.JSONField(default=dict, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("user", "status")),
            models.Index(fields=("request_path", "status")),
        ]

    def mark_confirmed(
        self,
        metadata: dict | None = None,
        payer: str | None = None,
        receipt_token: str | None = None,
        amount: Decimal | None = None,
    ):
        self.status = PaymentReceiptStatus.CONFIRMED
        self.verified_at = timezone.now()
        if payer:
            self.payer_address = payer
        if receipt_token:
            self.receipt_token = receipt_token
        if amount is not None:
            self.amount = amount
        if metadata:
            combined = self.metadata.copy()
            combined.update(metadata)
            self.metadata = combined
        self.save(
            update_fields=[
                "status",
                "verified_at",
                "payer_address",
                "metadata",
                "receipt_token",
                "amount",
                "updated_at",
            ]
        )

    def mark_rejected(self, reason: str = "", metadata: dict | None = None, receipt_token: str | None = None):
        combined = self.metadata.copy()
        if metadata:
            combined.update(metadata)
        if reason:
            combined["rejection_reason"] = reason
        if receipt_token:
            self.receipt_token = receipt_token
        self.status = PaymentReceiptStatus.REJECTED
        self.metadata = combined
        self.verified_at = timezone.now()
        self.save(update_fields=["status", "metadata", "receipt_token", "verified_at", "updated_at"])


class CreditUsageType(models.TextChoices):
    TOP_UP = "top_up", "Top-up"
    CONSUMPTION = "consumption", "Consumption"


class X402CreditPlan(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="x402_credit_plans",
    )
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=160)
    description = models.TextField(blank=True)
    amount = models.DecimalField(max_digits=20, decimal_places=8)
    currency = models.CharField(max_length=12, default="USDC")
    network = models.CharField(max_length=32, default="algorand")
    credits_per_payment = models.PositiveIntegerField(default=1)
    auto_renew = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    pattern = models.CharField(max_length=255, editable=False)
    metadata = models.JSONField(default=dict, blank=True)
    pay_to_address = models.CharField(max_length=128, blank=True)
    platform_fee_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "slug")
        indexes = [
            models.Index(fields=("user", "slug")),
            models.Index(fields=("user", "is_active")),
        ]

    def __str__(self):
        return f"{self.name} ({self.credits_per_payment} credits)"

    @property
    def tenant_prefix(self) -> str:
        return f"/paywall/tenant/{self.user_id}"

    def build_pattern(self) -> str:
        return f"{self.tenant_prefix}/credits/{self.slug}"

    def ensure_slug(self) -> None:
        if self.slug:
            return
        base = slugify(self.name) or "plan"
        slug = base
        counter = 1
        while X402CreditPlan.objects.filter(user=self.user, slug=slug).exclude(pk=self.pk).exists():
            slug = f"{base}-{counter}"
            counter += 1
        self.slug = slug

    def save(self, *args, **kwargs):
        self.ensure_slug()
        self.pattern = self.build_pattern()
        super().save(*args, **kwargs)


class CreditSubscription(models.Model):
    plan = models.ForeignKey(X402CreditPlan, on_delete=models.CASCADE, related_name="subscriptions")
    consumer_ref = models.CharField(max_length=160)
    credits_remaining = models.IntegerField(default=0)
    total_credits = models.IntegerField(default=0)
    last_purchase_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("plan", "consumer_ref")
        indexes = [
            models.Index(fields=("plan", "consumer_ref")),
            models.Index(fields=("consumer_ref",)),
        ]

    def __str__(self):
        return f"{self.consumer_ref} / {self.plan.name}"


class CreditUsage(models.Model):
    subscription = models.ForeignKey(CreditSubscription, on_delete=models.CASCADE, related_name="usages")
    receipt = models.ForeignKey(
        PaymentReceipt,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="credit_usages",
    )
    usage_type = models.CharField(max_length=16, choices=CreditUsageType.choices, default=CreditUsageType.TOP_UP)
    credits_delta = models.IntegerField()
    description = models.CharField(max_length=255, blank=True)
    fee_amount = models.DecimalField(max_digits=20, decimal_places=8, default=Decimal("0"))
    merchant_amount = models.DecimalField(max_digits=20, decimal_places=8, default=Decimal("0"))
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("subscription", "created_at")),
        ]

    def __str__(self):
        return f"{self.usage_type} {self.credits_delta} credits"
