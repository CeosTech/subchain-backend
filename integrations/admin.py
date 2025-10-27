# integrations/admin.py

from django.contrib import admin
from .models import Integration, IntegrationDeliveryLog, IntegrationStatus, DeliveryStatus
from .services import simulate_delivery


class IntegrationDeliveryInline(admin.TabularInline):
    model = IntegrationDeliveryLog
    extra = 0
    can_delete = False
    fields = ("event_type", "status", "response_code", "duration_ms", "created_at")
    readonly_fields = fields

@admin.register(Integration)
class IntegrationAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "type",
        "user",
        "status",
        "is_active",
        "last_success_at",
        "failure_count",
        "created_at",
    )
    list_filter = ("type", "status", "is_active")
    search_fields = ("name", "user__email", "endpoint_url")
    readonly_fields = (
        "user",
        "created_at",
        "updated_at",
        "last_success_at",
        "last_error_at",
        "failure_count",
        "last_error_message",
    )
    fieldsets = (
        (None, {
            "fields": ("user", "name", "type", "status", "is_active"),
        }),
        ("Connection", {
            "fields": ("endpoint_url", "auth_token", "config"),
        }),
        ("Health", {
            "fields": (
                "last_success_at",
                "last_error_at",
                "failure_count",
                "last_error_message",
            ),
        }),
        ("Metadata", {"fields": ("created_at", "updated_at")}),
    )
    inlines = [IntegrationDeliveryInline]
    actions = ["mark_as_healthy", "mark_as_failed", "send_test_ping"]

    def send_test_ping(self, request, queryset):
        for integration in queryset:
            simulate_delivery(integration, event_type="integration.test")
        self.message_user(request, f"Recorded test ping for {queryset.count()} integration(s).")

    send_test_ping.short_description = "Send test ping (mark healthy)"

    def mark_as_healthy(self, request, queryset):
        for integration in queryset:
            integration.mark_success()
        self.message_user(request, f"Marked {queryset.count()} integration(s) as healthy.")

    mark_as_healthy.short_description = "Mark selected integrations as healthy"

    def mark_as_failed(self, request, queryset):
        for integration in queryset:
            integration.mark_failure("Manually flagged as failed")
        self.message_user(request, f"Marked {queryset.count()} integration(s) as failed.")

    mark_as_failed.short_description = "Mark selected integrations as failed"
