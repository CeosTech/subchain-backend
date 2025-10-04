from django.contrib import admin
from .models import Notification, NotificationTemplate

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'channel', 'title', 'is_read', 'created_at', 'sent_at')
    search_fields = ('user__email', 'title', 'channel')
    list_filter = ('channel', 'is_read', 'created_at')

@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'subject', 'notification_type', 'is_active', 'created_at')
    search_fields = ('name', 'subject')
    list_filter = ('notification_type', 'is_active')
