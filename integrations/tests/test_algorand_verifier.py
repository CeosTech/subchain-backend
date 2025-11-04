from __future__ import annotations

import base64
import json
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings

from integrations.verifiers import algorand


@override_settings(
    X402_PAYTO_ADDRESS="RECEIVER123",
    ALGORAND_NETWORK="testnet",
    ALGO_INDEXER_URL="https://indexer.testnet.algorand.network",
    X402_ASSET_DECIMALS=6,
)
class AlgorandVerifierTests(SimpleTestCase):
    def setUp(self):
        self.payload = {
            "nonce": "nonce-123",
            "txid": "TESTTXID",
            "amount": "2.0",
            "asset_id": 10458941,
            "metadata": {"source": "unit-test"},
        }
        self.base_transaction = {
            "transaction": {
                "tx-type": "axfer",
                "sender": "SENDER123",
                "confirmed-round": 123456,
                "asset-transfer-transaction": {
                    "asset-id": 10458941,
                    "receiver": "RECEIVER123",
                    "amount": 2_000_000,
                },
                "note": base64.b64encode(b"nonce-123").decode(),
            }
        }

    def test_successful_verification_returns_metadata(self):
        mock_client = MagicMock()
        mock_client.transaction.return_value = self.base_transaction
        with patch("integrations.verifiers.algorand._get_indexer_client", return_value=mock_client):
            result = algorand.verify_receipt(json.dumps(self.payload), Decimal("1.5"), None)

        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "confirmed")
        self.assertEqual(result["nonce"], "nonce-123")
        self.assertEqual(result["amount"], "2")
        self.assertEqual(result["payer"], "SENDER123")
        self.assertIn("transaction_id", result)
        self.assertEqual(result["metadata"]["confirmed_round"], 123456)
        self.assertEqual(result["expected_receiver"], "RECEIVER123")

    def test_mismatched_receiver_rejected(self):
        transaction = json.loads(json.dumps(self.base_transaction))
        transaction["transaction"]["asset-transfer-transaction"]["receiver"] = "OTHER"
        mock_client = MagicMock()
        mock_client.transaction.return_value = transaction
        with patch("integrations.verifiers.algorand._get_indexer_client", return_value=mock_client):
            result = algorand.verify_receipt(json.dumps(self.payload), Decimal("1"), None)

        self.assertIsNone(result)

    def test_invalid_receipt_payload_returns_none(self):
        result = algorand.verify_receipt("not-json", Decimal("1"), None)
        self.assertIsNone(result)
