from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.config import settings

from .model import PublishedEvent


def build_event_envelope(event: PublishedEvent) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    envelope: dict[str, Any] = {
        "event_type": event.event_type,
        "event_id": f"evt-{uuid4().hex}",
        "created_at": now,
        "schema_version": settings.event_schema_version,
        "channel": event.channel,
        "payload": event.payload,
    }
    if event.correlation_id:
        envelope["correlation_id"] = event.correlation_id
    return envelope
