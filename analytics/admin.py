from django.contrib import admin
from .models import EventLog, AnalyticsLog

@admin.register(EventLog)
class EventLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'event_type', 'timestamp')
    list_filter = ('event_type', 'timestamp')
    ordering = ('-timestamp',)
    search_fields = ('user__email', 'event_type')

@admin.register(AnalyticsLog)
class AnalyticsLogAdmin(admin.ModelAdmin):
    list_display = ('event_type', 'created_at')
    ordering = ('-created_at',)
    search_fields = ('event_type',)
