from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.api.system_helpers import (
    build_metrics_lines,
    build_persistence_status,
    build_ready_content,
)
from app.ports import MatchingObservabilityPort, RuntimeStatusPort, StoreStatusPort


@dataclass(slots=True)
class SystemStatusService:
    runtime_status: RuntimeStatusPort
    signal_store_status: StoreStatusPort
    matching_observability: MatchingObservabilityPort
    started_at: float

    async def ready(self, *, request_id: str) -> tuple[int, dict[str, Any]]:
        return await build_ready_content(
            self.runtime_status,
            self.matching_observability,
            started_at=self.started_at,
            request_id=request_id,
        )

    async def metrics_lines(self, *, request_id: str) -> list[str]:
        return await build_metrics_lines(
            self.runtime_status,
            self.signal_store_status,
            self.matching_observability,
            started_at=self.started_at,
            request_id=request_id,
        )

    async def persistence(self, *, request_id: str) -> dict[str, Any]:
        return await build_persistence_status(
            self.runtime_status,
            self.signal_store_status,
            self.matching_observability,
            request_id=request_id,
        )
