from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),

    # Authentification et comptes
    path("api/auth/", include(("accounts.urls", "accounts"), namespace="accounts")),

    # Gestion des abonnements
    path("api/subscriptions/", include("subscriptions.urls")),

    # Paiements (à venir)
    path("api/payments/", include("payments.urls")),

    # Monnaies / Taux de change (à venir)
    path("api/currency/", include("currency.urls")),

    # Webhooks (à venir)
    path("api/webhooks/", include("webhooks.urls")),

    # Notifications (à venir)
    path("api/notifications/", include("notifications.urls")),

    # Analytics (à venir)
    path("api/analytics/", include("analytics.urls")),

    # Intégrations (à venir)
    path("api/integrations/", include("integrations.urls")),
]
