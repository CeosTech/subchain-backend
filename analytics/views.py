# analytics/views.py
from rest_framework import viewsets, permissions
from .models import AnalyticsLog
from .serializers import AnalyticsLogSerializer

class AnalyticsLogViewSet(viewsets.ModelViewSet):
    queryset = AnalyticsLog.objects.all()
    serializer_class = AnalyticsLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_queryset(self):
        if self.request.user.is_staff:
            return AnalyticsLog.objects.all()
        return AnalyticsLog.objects.filter(user=self.request.user)