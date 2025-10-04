# webhooks/urls.py
from django.urls import path
from .views import payment_webhook

urlpatterns = [
    path('payments/', payment_webhook, name='payment_webhook'),
]
