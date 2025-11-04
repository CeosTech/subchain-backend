# integrations/admin.py

from django.contrib import admin

from .models import (
    CreditSubscription,
    CreditUsage,
    DeliveryStatus,
    EndpointPricingRule,
    Integration,
    IntegrationDeliveryLog,
    IntegrationStatus,
    PaymentLink,
    PaymentLinkEvent,
    PaymentLinkType,
    PaymentReceipt,
    PaymentReceiptStatus,
    X402CreditPlan,
)
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


@admin.register(EndpointPricingRule)
class EndpointPricingRuleAdmin(admin.ModelAdmin):
    list_display = (
        "pattern",
        "amount",
        "currency",
        "network",
        "methods",
        "priority",
        "is_active",
        "user",
        "updated_at",
    )
    list_filter = ("currency", "network", "is_active")
    search_fields = ("pattern", "description", "user__email")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (
            "Rule",
            {"fields": ("user", "pattern", "methods", "amount", "currency", "network", "priority", "is_active")},
        ),
        ("Details", {"fields": ("description", "metadata", "created_at", "updated_at")}),
    )


@admin.register(PaymentReceipt)
class PaymentReceiptAdmin(admin.ModelAdmin):
    list_display = (
        "nonce",
        "user",
        "amount",
        "currency",
        "status",
        "network",
        "request_path",
        "verified_at",
        "created_at",
    )
    list_filter = ("status", "network", "currency")
    search_fields = ("nonce", "payer_address", "user__email", "request_path")
    readonly_fields = ("created_at", "updated_at", "verified_at")
    fieldsets = (
        (
            "Receipt",
            {"fields": ("user", "nonce", "receipt_token", "status", "network", "currency")},
        ),
        (
            "Payment",
            {"fields": ("amount", "payer_address", "request_path", "request_method")},
        ),
        (
            "Metadata",
            {"fields": ("metadata", "verified_at", "created_at", "updated_at")},
        ),
    )
    actions = ["mark_as_confirmed", "mark_as_rejected"]

    def mark_as_confirmed(self, request, queryset):
        updated = 0
        for receipt in queryset:
            if receipt.status != PaymentReceiptStatus.CONFIRMED:
                receipt.mark_confirmed()
                updated += 1
        self.message_user(request, f"Marked {updated} receipt(s) as confirmed.")

    mark_as_confirmed.short_description = "Mark selected receipts as confirmed"

    def mark_as_rejected(self, request, queryset):
        updated = 0
        for receipt in queryset:
            if receipt.status != PaymentReceiptStatus.REJECTED:
                receipt.mark_rejected("Marked via admin action")
                updated += 1
        self.message_user(request, f"Marked {updated} receipt(s) as rejected.")

    mark_as_rejected.short_description = "Mark selected receipts as rejected"


class PaymentLinkEventInline(admin.TabularInline):
    model = PaymentLinkEvent
    extra = 0
    readonly_fields = ("receipt", "payer_address", "amount", "fee_amount", "merchant_amount", "metadata", "created_at")


@admin.register(PaymentLink)
class PaymentLinkAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "kind",
        "user",
        "amount",
        "currency",
        "is_active",
        "pattern",
        "created_at",
    )
    list_filter = ("kind", "currency", "network", "is_active")
    search_fields = ("name", "slug", "user__email")
    readonly_fields = ("pattern", "created_at", "updated_at")
    inlines = [PaymentLinkEventInline]


@admin.register(X402CreditPlan)
class CreditPlanAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "user",
        "amount",
        "currency",
        "credits_per_payment",
        "auto_renew",
        "is_active",
        "created_at",
    )
    list_filter = ("currency", "network", "auto_renew", "is_active")
    search_fields = ("name", "slug", "user__email")
    readonly_fields = ("pattern", "created_at", "updated_at")


@admin.register(CreditSubscription)
class CreditSubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "plan",
        "consumer_ref",
        "credits_remaining",
        "total_credits",
        "last_purchase_at",
        "updated_at",
    )
    search_fields = ("consumer_ref", "plan__name", "plan__user__email")
    list_filter = ("plan",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(CreditUsage)
class CreditUsageAdmin(admin.ModelAdmin):
    list_display = (
        "subscription",
        "usage_type",
        "credits_delta",
        "fee_amount",
        "merchant_amount",
        "created_at",
    )
    list_filter = ("usage_type",)
    search_fields = ("subscription__consumer_ref", "subscription__plan__name")
    readonly_fields = ("created_at",)
