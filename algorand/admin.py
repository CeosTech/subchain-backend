from django.contrib import admin
from .models import SwapLog


@admin.register(SwapLog)
class SwapLogAdmin(admin.ModelAdmin):
    list_display = (
        "transaction",
        "from_currency",
        "to_currency",
        "amount_in",
        "amount_out",
        "status",
        "created_at",
    )
    list_filter = ("status", "from_currency", "to_currency")
    search_fields = ("transaction__id", "transaction__user__email", "tx_id")
    readonly_fields = ("created_at",)
