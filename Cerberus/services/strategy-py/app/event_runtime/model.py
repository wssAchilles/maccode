from __future__ import annotations

from typing import Any


class PublishedEvent:
    def __init__(
        self,
        *,
        channel: str,
        event_type: str,
        payload: dict[str, Any],
        correlation_id: str | None = None,
    ) -> None:
        self.channel = channel
        self.event_type = event_type
        self.payload = payload
        self.correlation_id = correlation_id
