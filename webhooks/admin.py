from django.contrib import admin
from .models import WebhookLog


@admin.register(WebhookLog)
class WebhookLogAdmin(admin.ModelAdmin):
    list_display = ("endpoint", "external_id", "success", "status_code", "created_at")
    list_filter = ("endpoint", "success")
    search_fields = ("external_id",)
    readonly_fields = ("payload", "headers", "response", "error_message", "created_at")
    ordering = ("-created_at",)
