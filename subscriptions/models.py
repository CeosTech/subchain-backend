# subscriptions/models.py
from django.db import models
from django.conf import settings
from django.utils import timezone

CURRENCY_CHOICES = [
    ("USD", "US Dollar"),
    ("EUR", "Euro"),
    ("ALGO", "Algorand"),
    ("USDC", "USDC (Algorand)"),
]

STATUS_CHOICES = [
    ("active", "Active"),
    ("cancelled", "Cancelled"),
    ("paused", "Paused"),
    ("trialing", "Trialing"),
    ("expired", "Expired"),
]

class Feature(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class SubscriptionPlan(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, choices=CURRENCY_CHOICES, default="USD")
    trial_days = models.PositiveIntegerField(default=0)
    features = models.ManyToManyField(Feature, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.price} {self.currency})"

class Subscriber(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.SET_NULL, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="trialing")
    start_date = models.DateTimeField(default=timezone.now)
    trial_end_date = models.DateTimeField(null=True, blank=True)
    renewal_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} → {self.plan.name if self.plan else 'No plan'}"

class PlanChangeLog(models.Model):
    subscriber = models.ForeignKey(Subscriber, on_delete=models.CASCADE)
    previous_plan = models.ForeignKey(SubscriptionPlan, on_delete=models.SET_NULL, null=True, related_name="previous_plan")
    new_plan = models.ForeignKey(SubscriptionPlan, on_delete=models.SET_NULL, null=True, related_name="new_plan")
    changed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.subscriber.user.email} changed plan on {self.changed_at.strftime('%Y-%m-%d')}"
