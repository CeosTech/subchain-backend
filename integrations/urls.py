# integrations/urls.py

from rest_framework.routers import DefaultRouter
from .views import IntegrationViewSet

router = DefaultRouter()
router.register(r'', IntegrationViewSet, basename='integration')

urlpatterns = router.urls
