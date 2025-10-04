from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from .models import Notification, NotificationTemplate
from .serializers import NotificationSerializer, NotificationTemplateSerializer
from .utils import send_email_notification, send_notification_from_template, send_sms_notification
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        notification = serializer.save()
        if notification.notification_type == 'email':
            send_email_notification(notification)
        elif notification.notification_type == 'sms':
            send_sms_notification(notification)


class NotificationTemplateViewSet(viewsets.ModelViewSet):
    queryset = NotificationTemplate.objects.all()
    serializer_class = NotificationTemplateSerializer
    permission_classes = [IsAdminUser]


class SendNotificationView(APIView):
    permission_classes = [IsAdminUser]  # ou un custom permission

    def post(self, request):
        template_name = request.data.get("template")
        user_email = request.data.get("email")
        context = request.data.get("context", {})

        if not template_name or not user_email:
            return Response({"error": "Missing template or email."}, status=400)

        result = send_notification_from_template(template_name, user_email, context)
        return Response(result, status=status.HTTP_200_OK)
