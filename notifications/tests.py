from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.core import mail

from notifications.models import Notification
from accounts.models import User


class NotificationAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="notify@example.com",
            password="pass1234",
            username="notify",
            wallet_address="NOTIFYWALLET",
        )
        self.client.force_authenticate(user=self.user)
        self.url = reverse("notifications-list")

    def test_create_email_notification_sets_sent_at(self):
        payload = {
            "user": self.user.id,
            "title": "Welcome",
            "message": "Hello from SubChain",
            "channel": "email",
        }

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        notification = Notification.objects.get(pk=response.data["id"])
        self.assertIsNotNone(notification.sent_at)
        self.assertEqual(len(mail.outbox), 1)

    def test_create_sms_notification_returns_201(self):
        payload = {
            "user": self.user.id,
            "title": "SMS Alert",
            "message": "This is a test.",
            "channel": "sms",
        }

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        notification = Notification.objects.get(pk=response.data["id"])
        self.assertIsNone(notification.sent_at)
