# subscriptions/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FeatureViewSet, SubscriptionPlanViewSet, SubscriberViewSet, renew_subscription

router = DefaultRouter()
router.register(r'features', FeatureViewSet)
router.register(r'plans', SubscriptionPlanViewSet)
router.register(r'subscribers', SubscriberViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path("renew/", renew_subscription, name="renew-subscription"),
    path('subscribe/', SubscriberViewSet.as_view({'post': 'subscribe'}), name='subscribe'),
    path('change-plan/', SubscriberViewSet.as_view({'post': 'change_plan'}), name='change-plan'),
]
