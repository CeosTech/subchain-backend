# integrations/urls.py

from rest_framework.routers import DefaultRouter

from .views import (
    CreditPlanViewSet,
    CreditSubscriptionViewSet,
    CreditUsageViewSet,
    EndpointPricingRuleViewSet,
    IntegrationViewSet,
    PaymentLinkViewSet,
    PaymentReceiptViewSet,
    PaymentWidgetViewSet,
)

router = DefaultRouter()
router.register(r"integrations", IntegrationViewSet, basename="integration")
router.register(r"x402/pricing-rules", EndpointPricingRuleViewSet, basename="x402-pricing-rule")
router.register(r"x402/receipts", PaymentReceiptViewSet, basename="x402-receipt")
router.register(r"x402/links", PaymentLinkViewSet, basename="x402-links")
router.register(r"x402/widgets", PaymentWidgetViewSet, basename="x402-widgets")
router.register(r"x402/credit-plans", CreditPlanViewSet, basename="x402-credit-plans")
router.register(r"x402/credit-subscriptions", CreditSubscriptionViewSet, basename="x402-credit-subscriptions")
router.register(r"x402/credit-usage", CreditUsageViewSet, basename="x402-credit-usage")

urlpatterns = router.urls
