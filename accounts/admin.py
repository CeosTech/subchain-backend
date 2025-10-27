from django.contrib import admin
from django.contrib.auth import get_user_model
from .models import UserProfile, UserSettings, UserActivity, EmailVerification


User = get_user_model()


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("email", "username", "wallet_address", "is_active", "is_staff")
    list_filter = ("is_staff", "is_active", "is_superuser")
    search_fields = ("email", "username", "wallet_address")
    ordering = ("email",)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "company_name", "is_individual")
    search_fields = ("user__email", "company_name")


@admin.register(UserSettings)
class UserSettingsAdmin(admin.ModelAdmin):
    list_display = ("user", "language", "timezone", "receive_emails")
    search_fields = ("user__email",)


@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    list_display = ("user", "action", "timestamp", "ip_address")
    search_fields = ("user__email", "action", "ip_address")


@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):
    list_display = ("user", "token", "created_at", "is_used")
    search_fields = ("user__email", "token")
