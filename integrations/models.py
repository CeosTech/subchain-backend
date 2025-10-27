# integrations/models.py

from django.conf import settings
from django.db import models
from django.utils import timezone

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
