from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import EmailVerification, PasswordResetToken, User


class EmailVerificationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="user@example.com",
            password="pass1234",
            username="user",
            wallet_address="WALLET123",
        )
        self.verify_url = reverse("accounts:verify-email")

    def test_verify_email_marks_user_verified(self):
        token = EmailVerification.objects.create(user=self.user)

        response = self.client.post(self.verify_url, {"token": str(token.token)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        token.refresh_from_db()
        self.assertTrue(self.user.is_verified)
        self.assertTrue(token.is_used)

    def test_verify_email_rejects_expired_token(self):
        token = EmailVerification.objects.create(user=self.user)
        EmailVerification.objects.filter(pk=token.pk).update(
            created_at=timezone.now() - timedelta(hours=25)
        )

        response = self.client.post(self.verify_url, {"token": str(token.token)})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        token.refresh_from_db()
        self.assertFalse(self.user.is_verified)
        self.assertFalse(token.is_used)


class PasswordResetTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="reset@example.com",
            password="pass1234",
            username="resetuser",
            wallet_address="RESETWALLET123",
        )
        self.forgot_url = reverse("accounts:forgot-password")
        self.reset_url = reverse("accounts:reset-password")

    def test_forgot_password_unknown_user_returns_404(self):
        response = self.client.post(self.forgot_url, {"email": "unknown@example.com"})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_reset_password_marks_token_used(self):
        token = PasswordResetToken.objects.create(user=self.user)
        response = self.client.post(
            self.reset_url,
            {
                "token": str(token.token),
                "new_password": "newpass123",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        token.refresh_from_db()
        self.assertTrue(token.is_used)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("newpass123"))
