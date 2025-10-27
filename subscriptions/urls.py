from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CouponViewSet,
    EventLogViewSet,
    InvoiceViewSet,
    PlanViewSet,
    SubscriptionViewSet,
)

router = DefaultRouter()
router.register(r"plans", PlanViewSet, basename="plan")
router.register(r"subscriptions", SubscriptionViewSet, basename="subscription")
router.register(r"invoices", InvoiceViewSet, basename="invoice")
router.register(r"coupons", CouponViewSet, basename="coupon")
router.register(r"events", EventLogViewSet, basename="event")

urlpatterns = [
    path("", include(router.urls)),
]
