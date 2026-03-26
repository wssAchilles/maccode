from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.api.system_helpers import (
    build_metrics_lines,
    build_persistence_status,
    build_ready_content,
)
from app.redis_worker import RedisMarketWorker
from app.signal_store import SignalStore


@dataclass(slots=True)
class SystemStatusService:
    worker: RedisMarketWorker
    signal_store: SignalStore
    started_at: float

    async def ready(self, *, request_id: str) -> tuple[int, dict[str, Any]]:
        return await build_ready_content(
            self.worker,
            started_at=self.started_at,
            request_id=request_id,
        )

    async def metrics_lines(self, *, request_id: str) -> list[str]:
        return await build_metrics_lines(
            self.worker,
            self.signal_store,
            started_at=self.started_at,
            request_id=request_id,
        )

    async def persistence(self, *, request_id: str) -> dict[str, Any]:
        return await build_persistence_status(
            self.worker,
            self.signal_store,
            request_id=request_id,
        )
