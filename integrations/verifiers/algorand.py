from __future__ import annotations

import base64
import binascii
import json
import logging
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Optional

from django.conf import settings

try:  # pragma: no cover - module availability depends on deployment
    from algosdk.v2client import indexer  # type: ignore
except ImportError:  # pragma: no cover
    indexer = None  # type: ignore

logger = logging.getLogger(__name__)


def verify_receipt(receipt: str, price: Decimal, request) -> Optional[Dict[str, Any]]:
    """
    Verify an x402 receipt by inspecting a USDC transfer on Algorand.

    The receipt is expected to be a JSON object (raw or base64-encoded) containing:
      - nonce: unique nonce included in the payment note
      - txid / transaction_id: the Algorand transaction ID
      - amount (optional): declared amount (used as secondary check)
      - asset_id (optional): ASA identifier (defaults to configured USDC asset)

    Returns a dict with payment metadata if confirmed, otherwise None.
    """
    payload = _load_receipt_payload(receipt)
    if not payload:
        return None

    nonce = payload.get("nonce")
    tx_id = payload.get("txid") or payload.get("transaction_id")
    if not nonce or not tx_id:
        logger.warning("Algorand verifier missing nonce or transaction id in receipt payload.")
        return None

    asset_id = _resolve_asset_id(payload.get("asset_id"))
    expected_receiver = (getattr(request, "x402_payto_address", "") if request is not None else "") or getattr(settings, "X402_PAYTO_ADDRESS", "")
    decimals = getattr(settings, "X402_ASSET_DECIMALS", 6)

    try:
        client = _get_indexer_client()
        tx_response = client.transaction(tx_id)
    except Exception:  # pragma: no cover - network errors logged but not fatal
        logger.exception("Algorand indexer lookup failed for transaction %s.", tx_id)
        return None

    transaction = tx_response.get("transaction")
    if not transaction:
        logger.warning("Algorand indexer returned an empty transaction for txid=%s", tx_id)
        return None

    if transaction.get("tx-type") != "axfer":
        logger.warning("Algorand transaction %s is not an asset transfer.", tx_id)
        return None

    transfer = transaction.get("asset-transfer-transaction") or {}
    if asset_id and transfer.get("asset-id") != asset_id:
        logger.warning(
            "Algorand transaction %s asset mismatch. expected=%s actual=%s",
            tx_id,
            asset_id,
            transfer.get("asset-id"),
        )
        return None

    receiver = transfer.get("receiver")
    if expected_receiver and receiver and receiver.lower() != expected_receiver.lower():
        logger.warning(
            "Algorand transaction %s receiver mismatch. expected=%s actual=%s",
            tx_id,
            expected_receiver,
            receiver,
        )
        return None

    amount_micro = transfer.get("amount")
    if amount_micro is None:
        logger.warning("Algorand transaction %s missing amount.", tx_id)
        return None

    amount_decimal = Decimal(amount_micro) / Decimal(10**decimals)
    if amount_decimal < price:
        logger.warning(
            "Algorand transaction %s amount %s below required price %s.",
            tx_id,
            amount_decimal,
            price,
        )
        return None

    note = _decode_note(transaction.get("note"))
    if note and nonce not in note:
        logger.warning("Algorand transaction %s note does not contain nonce %s.", tx_id, nonce)
        return None

    confirmed_round = transaction.get("confirmed-round")
    if not confirmed_round:
        logger.warning("Algorand transaction %s not yet confirmed.", tx_id)
        return None

    payer = transaction.get("sender")
    metadata = {
        "transaction_id": tx_id,
        "asset_id": transfer.get("asset-id"),
        "confirmed_round": confirmed_round,
        "receiver": receiver,
        "note": note,
    }

    declared_amount = payload.get("amount")
    if declared_amount:
        try:
            declared_decimal = Decimal(str(declared_amount))
            if declared_decimal > amount_decimal:
                metadata["declared_amount"] = str(declared_decimal)
        except (InvalidOperation, TypeError):
            logger.debug("Ignoring invalid declared amount in receipt payload: %s", declared_amount)

    payload_metadata = payload.get("metadata")
    if isinstance(payload_metadata, dict):
        metadata.update(payload_metadata)

    return {
        "status": "confirmed",
        "nonce": nonce,
        "amount": str(amount_decimal),
        "payer": payer,
        "transaction_id": tx_id,
        "expected_receiver": expected_receiver,
        "metadata": metadata,
    }


def _load_receipt_payload(receipt: str) -> Optional[Dict[str, Any]]:
    if not receipt:
        return None
    candidates = [receipt]
    try:
        decoded = base64.b64decode(receipt).decode("utf-8")
        candidates.append(decoded)
    except Exception:
        pass

    for candidate in candidates:
        try:
            data = json.loads(candidate)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            continue

    logger.warning("Unable to decode x402 receipt payload.")
    return None


def _get_indexer_client() -> indexer.IndexerClient:
    if indexer is None:  # pragma: no cover - defensive if SDK missing
        raise RuntimeError("algosdk must be installed to verify Algorand receipts.")
    token = getattr(settings, "ALGO_API_TOKEN", "")
    headers = {"X-API-Key": token} if token else {}
    return indexer.IndexerClient(token, getattr(settings, "ALGO_INDEXER_URL", ""), headers)


def _resolve_asset_id(payload_asset: Any) -> Optional[int]:
    if payload_asset:
        try:
            return int(payload_asset)
        except (TypeError, ValueError):
            logger.debug("Ignoring invalid asset id from receipt payload: %s", payload_asset)

    configured = getattr(settings, "X402_ASSET_ID", None)
    if configured:
        return configured

    network = getattr(settings, "ALGORAND_NETWORK", "testnet").lower()
    if network == "mainnet":
        return int(getattr(settings, "ALGORAND_USDC_ASSET_ID_MAINNET", 31566704))
    return int(getattr(settings, "ALGORAND_USDC_ASSET_ID_TESTNET", 10458941))


def _decode_note(note_field: Optional[str]) -> Optional[str]:
    if not note_field:
        return None
    try:
        decoded = base64.b64decode(note_field)
        return decoded.decode("utf-8", errors="ignore")
    except (ValueError, TypeError, binascii.Error):  # pragma: no cover - defensive
        return None
