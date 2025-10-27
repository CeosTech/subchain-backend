from decimal import Decimal
import importlib
import sys
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.test.utils import override_settings

from algosdk import account, mnemonic

from payments.models import CurrencyChoices, Transaction, TransactionStatus, TransactionType


def _reload_payments_services():
    if "payments.services" in sys.modules:
        del sys.modules["payments.services"]
    return importlib.import_module("payments.services")


class SwapServiceTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        priv_key, address = account.generate_account()
        phrase = mnemonic.from_private_key(priv_key)

        cls.override = override_settings(
            ALGORAND_ACCOUNT_ADDRESS=address,
            ALGORAND_ACCOUNT_MNEMONIC=phrase,
            ALGORAND_NETWORK="testnet",
            ALGORAND_SWAP_MAX_RETRIES=3,
        )
        cls.override.enable()
        cls.services = _reload_payments_services()

    @classmethod
    def tearDownClass(cls):
        cls.override.disable()
        super().tearDownClass()

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="swap@example.com",
            username="swapuser",
            password="pass1234",
            wallet_address="WALLET123",
        )
        self.transaction = Transaction.objects.create(
            user=self.user,
            amount=Decimal("1.00"),
            currency=CurrencyChoices.ALGO,
            type=TransactionType.RENEWAL,
            status=TransactionStatus.PENDING,
        )

    @mock.patch("payments.services._sleep")
    @mock.patch("payments.services.perform_swap_algo_to_usdc")
    def test_execute_swap_success_updates_transaction(self, mock_swap, mock_sleep):
        mock_sleep.side_effect = None
        mock_swap.return_value = {
            "status": "success",
            "algo_sent": 1_000_000,
            "usdc_received": 1_200_000,
            "tx_ids": ["TX123"],
            "confirmed_round": 1234,
        }

        result = self.services.execute_algo_to_usdc_swap(self.transaction)

        self.transaction.refresh_from_db()
        self.assertTrue(self.transaction.swap_completed)
        self.assertEqual(self.transaction.status, TransactionStatus.CONFIRMED)
        self.assertEqual(self.transaction.usdc_received, Decimal("1.200000"))
        self.assertIn("Swapped to USDC", self.transaction.notes)
        self.assertEqual(result["tx_ids"], ["TX123"])
        mock_swap.assert_called_once()

    @mock.patch("payments.services._sleep")
    @mock.patch("payments.services.perform_swap_algo_to_usdc")
    def test_execute_swap_failure_marks_transaction_failed(self, mock_swap, mock_sleep):
        mock_sleep.side_effect = None
        mock_swap.side_effect = Exception("network down")

        with self.assertRaises(self.services.SwapExecutionError):
            self.services.execute_algo_to_usdc_swap(self.transaction)

        self.transaction.refresh_from_db()
        self.assertFalse(self.transaction.swap_completed)
        self.assertEqual(self.transaction.status, TransactionStatus.FAILED)
        self.assertIn("Swap failed", self.transaction.notes)
        self.assertEqual(mock_swap.call_count, self.services.MAX_SWAP_ATTEMPTS)
