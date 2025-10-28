# webhooks/models.py
from django.db import models

class WebhookLog(models.Model):
    endpoint = models.CharField(max_length=255)
    external_id = models.CharField(max_length=255, blank=True, db_index=True)
    payload = models.JSONField()
    headers = models.JSONField(default=dict, blank=True)
    success = models.BooleanField(default=False)
    status_code = models.IntegerField(null=True, blank=True)
    response = models.JSONField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"WebhookLog [{self.endpoint}] @ {self.created_at}"

    class Meta:
        indexes = [
            models.Index(fields=["endpoint", "external_id"]),
        ]
