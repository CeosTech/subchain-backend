from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from django.utils import timezone

from .models import DeliveryStatus, Integration, IntegrationDeliveryLog

logger = logging.getLogger(__name__)


def record_delivery(
    *,
    integration: Integration,
    event_type: str,
    payload: Optional[Dict[str, Any]] = None,
    status: str = DeliveryStatus.SUCCESS,
    response_code: Optional[int] = None,
    response_body: str = "",
    error_message: str = "",
    duration_ms: Optional[int] = None,
) -> IntegrationDeliveryLog:
    """Persist a delivery attempt and update integration health."""

    log_entry = IntegrationDeliveryLog.objects.create(
        integration=integration,
        event_type=event_type,
        payload=payload or {},
        status=status,
        response_code=response_code,
        response_body=response_body[:2000],
        error_message=error_message[:2000],
        duration_ms=duration_ms,
    )

    if status == DeliveryStatus.SUCCESS:
        integration.mark_success()
    else:
        integration.mark_failure(error_message)

    logger.info(
        "Integration delivery %s for %s (%s)",
        status,
        integration.name,
        event_type,
    )
    return log_entry


def simulate_delivery(integration: Integration, event_type: str, payload: Optional[Dict[str, Any]] = None) -> IntegrationDeliveryLog:
    """Utility function for admin/test actions to record a successful delivery."""
    return record_delivery(
        integration=integration,
        event_type=event_type,
        payload=payload or {"test": timezone.now().isoformat()},
        status=DeliveryStatus.SUCCESS,
    )
