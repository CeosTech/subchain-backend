# subscriptions/admin.py
from django.contrib import admin
from .models import Feature, SubscriptionPlan, Subscriber, PlanChangeLog

@admin.register(Feature)
class FeatureAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')

@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'currency', 'trial_days', 'is_active', 'created_at')
    list_filter = ('currency', 'is_active')
    search_fields = ('name',)

@admin.register(Subscriber)
class SubscriberAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'status', 'start_date', 'renewal_date')
    list_filter = ('status',)

@admin.register(PlanChangeLog)
class PlanChangeLogAdmin(admin.ModelAdmin):
    list_display = ('subscriber', 'previous_plan', 'new_plan', 'changed_at')