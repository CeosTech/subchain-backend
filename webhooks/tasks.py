from celery import shared_task
from django.utils import timezone

from payments.models import Transaction, TransactionStatus
from payments.services import SwapExecutionError, execute_algo_to_usdc_swap
from webhooks.models import WebhookLog


@shared_task
def process_payment_webhook(log_id: int, transaction_id: int):
    log = WebhookLog.objects.get(id=log_id)
    try:
        tx = Transaction.objects.get(id=transaction_id)
        if tx.status != TransactionStatus.CONFIRMED:
            tx.status = TransactionStatus.CONFIRMED
            tx.confirmed_at = timezone.now()
            tx.notes = "Confirmed via webhook"
            tx.save(update_fields=["status", "confirmed_at", "notes"])

        result = execute_algo_to_usdc_swap(tx)
        log.success = result.get("status") == "success"
        log.response = result
        log.status_code = 200 if log.success else 502
        log.save()
        if not log.success:
            raise SwapExecutionError(result.get("message"))
    except (Transaction.DoesNotExist, SwapExecutionError) as exc:
        log.success = False
        log.error_message = str(exc)
        log.status_code = 500
        log.save()
        raise
