from __future__ import annotations

from decimal import Decimal
from typing import Optional

from django.db import transaction
from django.utils import timezone

from payments.models import CurrencyChoices as PaymentCurrencyChoices
from payments.models import Transaction, TransactionStatus, TransactionType
from payments.utils import calculate_fees
from subscriptions.models import Invoice, InvoiceStatus, PaymentIntent, PaymentIntentStatus
from subscriptions.services.events import EventRecorder


class PaymentIntentService:
    def __init__(
        self,
        *,
        event_recorder: Optional[EventRecorder] = None,
        swap_executor=None,
        swap_error_class=None,
        now=None,
        unit_amount_quantize: str = "0.01",
    ):
        self.events = event_recorder or EventRecorder()
        self._swap_executor = swap_executor
        self._swap_error_class = swap_error_class
        self._now = now or timezone.now
        self._unit_quantize = Decimal(unit_amount_quantize)

    def process_invoice(self, invoice: Invoice, *, transaction_type: TransactionType = TransactionType.SUBSCRIPTION) -> PaymentIntent:
        with transaction.atomic():
            payment_intent, created = PaymentIntent.objects.select_for_update().get_or_create(
                invoice=invoice,
                defaults={
                    "status": PaymentIntentStatus.PROCESSING,
                    "amount": invoice.total,
                    "currency": invoice.currency,
                },
            )
            if not created:
                payment_intent.amount = invoice.total
                payment_intent.currency = invoice.currency
                payment_intent.status = PaymentIntentStatus.PROCESSING
                payment_intent.save(update_fields=["amount", "currency", "status", "updated_at"])

            if invoice.total <= 0:
                return self._mark_free_invoice(invoice, payment_intent)

        swap_executor, swap_error_class = self._ensure_swap_components()

        payment_intent.refresh_from_db()
        invoice.refresh_from_db()

        txn = self._create_transaction(invoice, transaction_type)

        try:
            result = swap_executor(txn)
        except swap_error_class as exc:
            payment_intent.status = PaymentIntentStatus.FAILED
            payment_intent.attempts += 1
            payment_intent.last_error = str(exc)
            payment_intent.save(update_fields=["status", "attempts", "last_error", "updated_at"])

            self.events.record(
                "invoice.payment_failed",
                resource_type="invoice",
                resource_id=invoice.id,
                payload={"error": str(exc)},
            )
            raise
        except Exception as exc:  # pragma: no cover - unexpected errors
            payment_intent.status = PaymentIntentStatus.FAILED
            payment_intent.attempts += 1
            payment_intent.last_error = str(exc)
            payment_intent.save(update_fields=["status", "attempts", "last_error", "updated_at"])
            self.events.record(
                "invoice.payment_failed",
                resource_type="invoice",
                resource_id=invoice.id,
                payload={"error": str(exc)},
            )
            raise

        payment_intent.status = PaymentIntentStatus.SUCCEEDED
        payment_intent.swap_tx_ids = result.get("tx_ids", [])
        if result.get("confirmed_round") is not None:
            payment_intent.confirmed_round = result["confirmed_round"]
        usdc_micro = result.get("usdc_received")
        if usdc_micro is not None:
            payment_intent.usdc_received = (Decimal(usdc_micro) / Decimal("1000000")).quantize(Decimal("0.000001"))
        payment_intent.attempts += 1
        payment_intent.last_error = ""
        payment_intent.save(update_fields=["status", "swap_tx_ids", "confirmed_round", "usdc_received", "attempts", "last_error", "updated_at"])

        invoice.status = InvoiceStatus.PAID
        invoice.paid_at = self._now()
        invoice.save(update_fields=["status", "paid_at"])

        self.events.record(
            "invoice.paid",
            resource_type="invoice",
            resource_id=invoice.id,
            payload={
                "payment_intent": payment_intent.id,
                "tx_ids": payment_intent.swap_tx_ids,
            },
        )
        return payment_intent

    def _mark_free_invoice(self, invoice: Invoice, payment_intent: PaymentIntent) -> PaymentIntent:
        invoice.status = InvoiceStatus.PAID
        invoice.paid_at = self._now()
        invoice.save(update_fields=["status", "paid_at"])

        payment_intent.status = PaymentIntentStatus.SUCCEEDED
        payment_intent.attempts += 1
        payment_intent.last_error = ""
        payment_intent.save(update_fields=["status", "attempts", "last_error", "updated_at"])

        self.events.record(
            "invoice.paid",
            resource_type="invoice",
            resource_id=invoice.id,
            payload={"free": True},
        )
        return payment_intent

    def _create_transaction(self, invoice: Invoice, transaction_type: TransactionType) -> Transaction:
        amount_2dp = invoice.total.quantize(self._unit_quantize)
        platform_fee, net_amount = calculate_fees(amount_2dp)

        txn = Transaction.objects.create(
            user=invoice.user,
            amount=amount_2dp,
            currency=invoice.currency if invoice.currency in PaymentCurrencyChoices.values else PaymentCurrencyChoices.ALGO,
            type=transaction_type,
            status=TransactionStatus.PENDING,
            platform_fee=platform_fee.quantize(self._unit_quantize),
            net_amount=net_amount.quantize(self._unit_quantize),
        )
        return txn

    def _ensure_swap_components(self):
        if self._swap_executor is not None and self._swap_error_class is not None:
            return self._swap_executor, self._swap_error_class
        from payments.services import SwapExecutionError, execute_algo_to_usdc_swap

        self._swap_executor = execute_algo_to_usdc_swap
        self._swap_error_class = SwapExecutionError
        return self._swap_executor, self._swap_error_class
