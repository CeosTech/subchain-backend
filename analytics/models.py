# analytics/models.py
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class EventLog(models.Model):
    EVENT_TYPES = [
        ("login", "Login"),
        ("subscription_created", "Subscription Created"),
        ("subscription_renewed", "Subscription Renewed"),
        ("payment_received", "Payment Received"),
        ("plan_changed", "Plan Changed"),
        ("notification_sent", "Notification Sent"),
        ("custom", "Custom Event")
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES)
    timestamp = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"{self.event_type} by {self.user} at {self.timestamp}"


class AnalyticsLog(models.Model):
    event_type = models.CharField(max_length=100)
    payload = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.event_type} @ {self.created_at}"