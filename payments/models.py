# payments/models.py

from django.conf import settings
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

CURRENCY_CHOICES = [
    ("ALGO", "Algorand"),
    ("USDC", "USDC (Algorand)"),
]

TRANSACTION_TYPE = [
    ("subscription", "New Subscription"),
    ("renewal", "Renewal"),
    ("manual", "Manual Payment"),
]

TRANSACTION_STATUS = [
    ("pending", "Pending"),
    ("confirmed", "Confirmed"),
    ("failed", "Failed"),
    ("refunded", "Refunded"),
]

class Transaction(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="transactions")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, choices=[("ALGO", "Algorand"), ("USDC", "USDC")])
    type = models.CharField(max_length=20, choices=[("subscription", "Subscription"), ("renewal", "Renewal")])
    status = models.CharField(max_length=20, choices=[("pending", "Pending"), ("confirmed", "Confirmed"), ("failed", "Failed")], default="pending")
    platform_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)  # nouveau champ
    net_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)     # montant après frais
    algo_tx_id = models.CharField(max_length=128, blank=True, null=True)
    usdc_received = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.user.email} - {self.amount} {self.currency} ({self.status})"