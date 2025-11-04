from django.urls import path

from .paywall_views import CreditPlanPaywallView, PaymentLinkPaywallView

urlpatterns = [
    path("tenant/<int:tenant_id>/links/<slug:slug>/", PaymentLinkPaywallView.as_view(), name="x402-link-paywall"),
    path("tenant/<int:tenant_id>/widgets/<slug:slug>/", PaymentLinkPaywallView.as_view(), name="x402-widget-paywall"),
    path("tenant/<int:tenant_id>/credits/<slug:slug>/", CreditPlanPaywallView.as_view(), name="x402-credit-paywall"),
]
