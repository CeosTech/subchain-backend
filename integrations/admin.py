# integrations/admin.py

from django.contrib import admin
from .models import Integration

@admin.register(Integration)
class IntegrationAdmin(admin.ModelAdmin):
    list_display = ("name", "type", "user", "is_active", "created_at")
    list_filter = ("type", "is_active")
    search_fields = ("name", "user__email")
