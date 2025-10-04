# payments/admin.py

from django.contrib import admin
from .models import Transaction

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("user", "amount", "currency", "type", "status", "created_at")
    list_filter = ("currency", "status", "type")
    search_fields = ("user__email", "algo_tx_id")
    ordering = ("-created_at",)
