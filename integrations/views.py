# integrations/views.py

from rest_framework import viewsets, permissions
from .models import Integration
from .serializers import IntegrationSerializer

class IntegrationViewSet(viewsets.ModelViewSet):
    serializer_class = IntegrationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Integration.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
