# integrations/models.py

from django.db import models
from django.conf import settings

INTEGRATION_TYPES = [
    ("webhook", "Webhook"),
    ("discord", "Discord"),
    ("slack", "Slack"),
    ("zapier", "Zapier"),
    ("stripe", "Stripe"),
    ("walletconnect", "WalletConnect"),
    ("custom", "Custom"),
]

class Integration(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="integrations")
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=30, choices=INTEGRATION_TYPES, default="webhook")
    config = models.JSONField(default=dict)  # Stocke token, URL, params selon le type
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.type})"
