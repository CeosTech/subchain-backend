from decimal import Decimal
from datetime import timedelta

from django.conf import settings
from django.contrib import admin
from django.template.response import TemplateResponse
from django.urls import path
from django.utils import timezone
from django.db.models import Sum, Count, F, DecimalField
from django.db.models.functions import Coalesce

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
    CheckoutSession,
)
from payments.models import Transaction, TransactionStatus
from subscriptions.models import InvoiceStatus, SubscriptionStatus


class PlanFeatureInline(admin.TabularInline):
    model = PlanFeature
    extra = 1


class PriceTierInline(admin.TabularInline):
    model = PriceTier
    extra = 0


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "created_by", "amount", "currency", "interval", "trial_days", "is_active")
    list_filter = ("currency", "interval", "is_active")
    search_fields = ("code", "name", "created_by__email")
    inlines = [PlanFeatureInline, PriceTierInline]
    actions = ["deploy_contract_action"]

    def deploy_contract_action(self, request, queryset):
        deployed = 0
        for plan in queryset:
            if plan.contract_app_id:
                continue

            config = SubscriptionContractConfig(
                plan_id=plan.id,
                price_micro_algo=int(plan.amount * Decimal("1000000")),
                renew_interval_rounds=30 * 60,  # placeholder
                treasury_address=settings.ALGORAND_ACCOUNT_ADDRESS,
            )
            app_id = deploy_subscription_contract(config)
            plan.contract_app_id = app_id
            plan.save(update_fields=["contract_app_id"])
            deployed += 1

        self.message_user(request, f"Deployed contracts for {deployed} plan(s).")

    deploy_contract_action.short_description = "Deploy Algorand subscription contract"


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


@admin.register(CheckoutSession)
class CheckoutSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "plan", "status", "expires_at", "created_at")
    list_filter = ("status", "plan__code")
    search_fields = ("id", "user__email", "plan__code")
    autocomplete_fields = ("user", "plan", "coupon")


def founder_insights_view(request):
    period_start = timezone.now() - timedelta(days=30)

    active_statuses = [SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING]
    subscriptions_qs = Subscription.objects.filter(status__in=active_statuses)

    mrr = subscriptions_qs.aggregate(
        total=Coalesce(
            Sum(F("plan__amount") * F("quantity"), output_field=DecimalField(max_digits=14, decimal_places=6)),
            Decimal("0"),
        )
    )["total"]

    paid_invoices = Invoice.objects.filter(status=InvoiceStatus.PAID, paid_at__isnull=False)
    net_mrr = paid_invoices.filter(paid_at__gte=period_start).aggregate(
        total=Coalesce(Sum("total"), Decimal("0"))
    )["total"]

    churn_count = Subscription.objects.filter(
        status=SubscriptionStatus.CANCELED,
        ended_at__isnull=False,
        ended_at__gte=period_start,
    ).count()

    swap_stats = Transaction.objects.filter(
        status=TransactionStatus.CONFIRMED,
        created_at__gte=period_start,
    ).aggregate(
        volume=Coalesce(Sum("usdc_received"), Decimal("0")),
        count=Count("id"),
    )
    swap_volume = swap_stats["volume"]
    swap_count = swap_stats["count"]
    swap_avg = swap_volume / swap_count if swap_count else Decimal("0")

    invoices_count = Invoice.objects.filter(issued_at__gte=period_start).count()

    metrics = {
        "currency": subscriptions_qs.values_list("plan__currency", flat=True).first() or "ALGO",
        "mrr": mrr,
        "net_mrr": net_mrr,
        "churn_count": churn_count,
        "swap_volume_usdc": swap_volume,
        "swap_count": swap_count,
        "swap_avg_usdc": swap_avg,
        "active_subscriptions": subscriptions_qs.filter(status=SubscriptionStatus.ACTIVE).count(),
        "trialing_subscriptions": Subscription.objects.filter(status=SubscriptionStatus.TRIALING).count(),
        "past_due_subscriptions": Subscription.objects.filter(status=SubscriptionStatus.PAST_DUE).count(),
        "invoices_count": invoices_count,
    }

    context = {**admin.site.each_context(request), "metrics": metrics, "period_start": period_start}
    return TemplateResponse(request, "subscriptions/founder_insights.html", context)


def _admin_urls_with_founder_insights(original_get_urls):
    def get_urls():
        custom_urls = [
            path("founder-insights/", admin.site.admin_view(founder_insights_view), name="founder-insights"),
        ]
        return custom_urls + original_get_urls()

    return get_urls


admin.site.get_urls = _admin_urls_with_founder_insights(admin.site.get_urls)
