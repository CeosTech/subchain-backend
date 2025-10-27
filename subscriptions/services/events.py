from __future__ import annotations

from typing import Any, Optional

from subscriptions.models import EventLog


class EventRecorder:
    """Facade around the EventLog model."""

    def record(
        self,
        event_type: str,
        *,
        resource_type: str,
        resource_id: str,
        payload: Optional[dict[str, Any]] = None,
        timestamp=None,
    ) -> EventLog:
        entry = EventLog(
            event_type=event_type,
            resource_type=resource_type,
            resource_id=str(resource_id),
            payload=payload or {},
        )
        if timestamp is not None:
            entry.created_at = timestamp
        entry.save()
        return entry
