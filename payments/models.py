# payments/models.py

from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class CurrencyChoices(models.TextChoices):
    ALGO = "ALGO", "Algorand"
    USDC = "USDC", "USDC (Algorand)"


class TransactionType(models.TextChoices):
    SUBSCRIPTION = "subscription", "New Subscription"
    RENEWAL = "renewal", "Renewal"
    MANUAL = "manual", "Manual Payment"


class TransactionStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    CONFIRMED = "confirmed", "Confirmed"
    FAILED = "failed", "Failed"
    REFUNDED = "refunded", "Refunded"


class Transaction(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="transactions")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, choices=CurrencyChoices.choices)
    type = models.CharField(max_length=20, choices=TransactionType.choices)
    status = models.CharField(max_length=20, choices=TransactionStatus.choices, default=TransactionStatus.PENDING)
    platform_fee = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    net_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    algo_tx_id = models.CharField(max_length=128, blank=True, null=True)
    usdc_received = models.DecimalField(max_digits=12, decimal_places=6, null=True, blank=True)
    swap_completed = models.BooleanField(default=False)
    payout_tx_id = models.CharField(max_length=128, blank=True, null=True)
    platform_fee_tx_id = models.CharField(max_length=128, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.user.email} - {self.amount} {self.currency} ({self.status})"
