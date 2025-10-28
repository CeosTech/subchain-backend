from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from payments.models import Transaction, CurrencyChoices, TransactionType
from webhooks.models import WebhookLog
from webhooks.tasks import process_payment_webhook


class WebhookTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="webhook@example.com",
            password="pass1234",
            username="webuser",
            wallet_address="WALLET123",
        )
        self.transaction = Transaction.objects.create(
            user=self.user,
            amount="10.00",
            currency=CurrencyChoices.ALGO,
            type=TransactionType.SUBSCRIPTION,
        )

    @mock.patch("webhooks.tasks.execute_algo_to_usdc_swap")
    def test_payment_webhook(self, mock_swap):
        mock_swap.return_value = {"status": "success"}
        url = reverse("payment_webhook")
        payload = {"transaction_id": self.transaction.id}
        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        log = WebhookLog.objects.get(external_id=str(self.transaction.id))
        process_payment_webhook(log.id, self.transaction.id)
        log.refresh_from_db()
        self.assertTrue(log.success)

    @mock.patch("webhooks.tasks.execute_algo_to_usdc_swap")
    def test_duplicate_webhook(self, mock_swap):
        mock_swap.return_value = {"status": "success"}
        url = reverse("payment_webhook")
        payload = {"transaction_id": self.transaction.id}
        self.client.post(url, payload, format="json")
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(WebhookLog.objects.filter(external_id=str(self.transaction.id)).count(), 1)
