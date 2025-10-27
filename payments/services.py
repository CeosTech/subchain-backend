from __future__ import annotations

import logging
from decimal import Decimal
from typing import Dict

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils import timezone

from algosdk import mnemonic

from algorand.utils import TinymanSwapError, perform_swap_algo_to_usdc
from .models import Transaction, TransactionStatus

logger = logging.getLogger(__name__)

ACCOUNT_ADDRESS = getattr(settings, "ALGORAND_ACCOUNT_ADDRESS", "")
ACCOUNT_MNEMONIC = getattr(settings, "ALGORAND_ACCOUNT_MNEMONIC", "")
ACCOUNT_PRIVATE_KEY = None


def _ensure_credentials():
    global ACCOUNT_PRIVATE_KEY

    if not ACCOUNT_ADDRESS or not ACCOUNT_MNEMONIC:
        raise ImproperlyConfigured(
            "ALGORAND_ACCOUNT_ADDRESS and ALGORAND_ACCOUNT_MNEMONIC must be configured to execute swaps."
        )

    if ACCOUNT_PRIVATE_KEY is None:
        try:
            ACCOUNT_PRIVATE_KEY = mnemonic.to_private_key(ACCOUNT_MNEMONIC)
        except Exception as exc:  # pragma: no cover - invalid configuration is caught during startup
            raise ImproperlyConfigured("ALGORAND_ACCOUNT_MNEMONIC is invalid.") from exc

MAX_SWAP_ATTEMPTS = max(1, int(getattr(settings, "ALGORAND_SWAP_MAX_RETRIES", 3)))
RETRY_DELAY_SECONDS = float(getattr(settings, "ALGORAND_SWAP_RETRY_DELAY_SECONDS", 1.5))


class SwapExecutionError(Exception):
    """Raised when the swap cannot be executed after retries."""


def _append_note(transaction: Transaction, note: str) -> None:
    transaction.notes = f"{transaction.notes} | {note}".strip(" |") if transaction.notes else note


def _apply_swap_success(transaction: Transaction, usdc_micro: int) -> None:
    usdc_amount = (Decimal(usdc_micro) / Decimal("1000000")).quantize(Decimal("0.000001"))
    transaction.usdc_received = usdc_amount
    _append_note(transaction, f"Swapped to USDC: {usdc_amount}")
    transaction.swap_completed = True
    if transaction.status != TransactionStatus.CONFIRMED:
        transaction.status = TransactionStatus.CONFIRMED
    if not transaction.confirmed_at:
        transaction.confirmed_at = timezone.now()
    transaction.save(update_fields=["usdc_received", "swap_completed", "notes", "status", "confirmed_at"])


def _apply_swap_failure(transaction: Transaction, reason: str) -> None:
    _append_note(transaction, f"Swap failed: {reason}")
    transaction.swap_completed = False
    transaction.status = TransactionStatus.FAILED
    transaction.save(update_fields=["notes", "swap_completed", "status"])


def execute_algo_to_usdc_swap(transaction: Transaction) -> Dict:
    """
    Trigger the ALGO ➜ USDC swap for a transaction and persist the outcome.
    Returns the provider response on success, raises SwapExecutionError otherwise.
    """
    amount_micro = int(transaction.amount * Decimal("1000000"))
    last_error: Exception | None = None

    for attempt in range(1, MAX_SWAP_ATTEMPTS + 1):
        try:
            logger.info(
                "Initiating Tinyman swap attempt %s/%s for transaction=%s amount=%sµALGO",
                attempt,
                MAX_SWAP_ATTEMPTS,
                transaction.id,
                amount_micro,
            )

            _ensure_credentials()
            result = perform_swap_algo_to_usdc(
                sender_address=ACCOUNT_ADDRESS,
                sender_private_key=ACCOUNT_PRIVATE_KEY,
                amount_algo=amount_micro,
                transaction_id=transaction.id,
            )

            if result.get("status") != "success":
                raise TinymanSwapError(result.get("message", "Unknown Tinyman error"))

            usdc_micro = result.get("usdc_received")
            if usdc_micro is None:
                raise TinymanSwapError("Tinyman response missing usdc_received amount.")

            _apply_swap_success(transaction, usdc_micro)
            return result
        except Exception as exc:  # pragma: no cover - retry loop handles specific cases below
            last_error = exc
            logger.warning(
                "Tinyman swap attempt %s/%s failed for transaction=%s: %s",
                attempt,
                MAX_SWAP_ATTEMPTS,
                transaction.id,
                exc,
            )
            if attempt == MAX_SWAP_ATTEMPTS:
                break
            _sleep(RETRY_DELAY_SECONDS * attempt)

    assert last_error is not None  # for type checkers
    _apply_swap_failure(transaction, str(last_error))
    raise SwapExecutionError("Unable to complete ALGO→USDC swap.") from last_error


def _sleep(duration: float) -> None:
    """Expose sleep for easier mocking in tests."""
    import time

    time.sleep(duration)
