from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.ports import MatchingObservabilityPort, RuntimeStatusPort, StoreStatusPort
from app.system_status_query import (
    PersistenceStatusResult,
    build_metrics_lines,
    build_persistence_status,
    build_ready_content,
)


@dataclass(frozen=True, slots=True)
class ReadyResult:
    status_code: int
    payload: dict[str, Any]


class SystemStatusApplicationService:
    def __init__(
        self,
        *,
        runtime_status: RuntimeStatusPort,
        signal_store_status: StoreStatusPort,
        matching_observability: MatchingObservabilityPort,
        started_at: float,
    ) -> None:
        self._runtime_status = runtime_status
        self._signal_store_status = signal_store_status
        self._matching_observability = matching_observability
        self._started_at = started_at

    async def ready(self, *, request_id: str) -> ReadyResult:
        status_code, payload = await build_ready_content(
            self._runtime_status,
            self._matching_observability,
            started_at=self._started_at,
            request_id=request_id,
        )
        return ReadyResult(status_code=status_code, payload=payload)

    async def metrics_lines(self, *, request_id: str) -> list[str]:
        return await build_metrics_lines(
            self._runtime_status,
            self._signal_store_status,
            self._matching_observability,
            started_at=self._started_at,
            request_id=request_id,
        )

    async def persistence_status(self, *, request_id: str) -> PersistenceStatusResult:
        return await build_persistence_status(
            self._runtime_status,
            self._signal_store_status,
            self._matching_observability,
            request_id=request_id,
        )
