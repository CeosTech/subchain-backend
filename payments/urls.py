# payments/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TransactionViewSet, algo_payment_webhook, get_algo_qr

router = DefaultRouter()
router.register(r'', TransactionViewSet, basename="transaction")

urlpatterns = [
    path('', include(router.urls)),
    path("webhook/algo-confirm/", algo_payment_webhook, name="algo_webhook"),
    path("qr/", get_algo_qr, name="generate_qr"),
]
