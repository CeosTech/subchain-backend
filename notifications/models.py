from django.db import models
from django.conf import settings

NOTIFICATION_CHANNELS = [
    ("email", "Email"),
    ("webhook", "Webhook"),
    ("sms", "SMS"),
    ("in_app", "In-App"),
]

class Notification(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications"
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    channel = models.CharField(max_length=20, choices=NOTIFICATION_CHANNELS, default="email")
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.channel.upper()} to {self.user.email} — {self.title}"
    
    
NOTIFICATION_TYPE_CHOICES = [
    ("email", "Email"),
    ("sms", "SMS"),           # Tu peux ajouter plus tard Twilio, etc.
    ("inapp", "In-App Message")  # Si tu veux des notifications internes à l’UI
]

class NotificationTemplate(models.Model):
    name = models.CharField(max_length=100, unique=True)  # ex: "welcome_email"
    subject = models.CharField(max_length=200, blank=True)
    message = models.TextField()
    notification_type = models.CharField(max_length=10, choices=NOTIFICATION_TYPE_CHOICES, default="email")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.notification_type})"
