# webhooks/models.py
from django.db import models

class WebhookLog(models.Model):
    endpoint = models.CharField(max_length=255)
    payload = models.JSONField()
    success = models.BooleanField(default=False)
    response = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"WebhookLog [{self.endpoint}] @ {self.created_at}"
