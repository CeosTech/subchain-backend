# currency/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CurrencyViewSet, ExchangeRateViewSet, convert_currency

router = DefaultRouter()
router.register(r'currencies', CurrencyViewSet)
router.register(r'exchange-rates', ExchangeRateViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('convert/', convert_currency, name='convert-currency'),
]
