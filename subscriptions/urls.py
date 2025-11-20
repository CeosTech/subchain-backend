from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CheckoutSessionViewSet,
    CouponViewSet,
    EventLogViewSet,
    InvoiceViewSet,
    PlanViewSet,
    PlanPublicRetrieveView,
    SubscriptionViewSet,
)

router = DefaultRouter()
router.register(r"plans", PlanViewSet, basename="plan")
router.register(r"subscriptions", SubscriptionViewSet, basename="subscription")
router.register(r"invoices", InvoiceViewSet, basename="invoice")
router.register(r"coupons", CouponViewSet, basename="coupon")
router.register(r"events", EventLogViewSet, basename="event")
router.register(r"checkout-sessions", CheckoutSessionViewSet, basename="checkoutsession")

urlpatterns = [
    path("plans/public/<slug:code>/", PlanPublicRetrieveView.as_view(), name="plan-public-detail"),
    path("", include(router.urls)),
]
