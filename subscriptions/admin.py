from django.contrib import admin

from .models import (
    Coupon,
    EventLog,
    Invoice,
    InvoiceLineItem,
    PaymentIntent,
    Plan,
    PlanFeature,
    PriceTier,
    Subscription,
)


class PlanFeatureInline(admin.TabularInline):
    model = PlanFeature
    extra = 1


class PriceTierInline(admin.TabularInline):
    model = PriceTier
    extra = 0


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "amount", "currency", "interval", "trial_days", "is_active")
    list_filter = ("currency", "interval", "is_active")
    search_fields = ("code", "name")
    inlines = [PlanFeatureInline, PriceTierInline]


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "duration", "percent_off", "amount_off", "currency", "max_redemptions")
    list_filter = ("duration", "currency")
    search_fields = ("code", "name")


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("user", "plan", "status", "current_period_end", "cancel_at_period_end", "created_at")
    list_filter = ("status", "plan__code")
    search_fields = ("user__email", "plan__code", "wallet_address")
    autocomplete_fields = ("user", "plan", "coupon")


class InvoiceLineItemInline(admin.TabularInline):
    model = InvoiceLineItem
    extra = 0


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("number", "subscription", "status", "total", "currency", "issued_at", "paid_at")
    list_filter = ("status", "currency")
    search_fields = ("number", "subscription__user__email", "subscription__plan__code")
    inlines = [InvoiceLineItemInline]
    autocomplete_fields = ("subscription", "user")


@admin.register(PaymentIntent)
class PaymentIntentAdmin(admin.ModelAdmin):
    list_display = ("invoice", "status", "amount", "currency", "attempts", "updated_at")
    list_filter = ("status", "currency")
    search_fields = ("invoice__number",)


@admin.register(EventLog)
class EventLogAdmin(admin.ModelAdmin):
    list_display = ("event_type", "resource_type", "resource_id", "created_at")
    list_filter = ("event_type", "resource_type")
    search_fields = ("resource_id", "event_type")
