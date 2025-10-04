# analytics/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AnalyticsLogViewSet

router = DefaultRouter()
router.register(r'logs', AnalyticsLogViewSet, basename='analytics-log')

urlpatterns = [
    path('', include(router.urls)),
]