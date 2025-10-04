from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import NotificationViewSet, NotificationTemplateViewSet, SendNotificationView

router = DefaultRouter()
router.register(r'', NotificationViewSet, basename='notifications')
router.register(r'templates', NotificationTemplateViewSet, basename='notification-templates')

urlpatterns = [
    path('', include(router.urls)),
    path("send-notification/", SendNotificationView.as_view(), name="send-notification"),
]
