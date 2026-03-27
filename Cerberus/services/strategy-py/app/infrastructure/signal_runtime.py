from __future__ import annotations

from app.redis_worker import RedisMarketWorker
from app.schemas import Signal, TickEvent


class WorkerSignalRuntimeAdapter:
    def __init__(self, worker: RedisMarketWorker) -> None:
        self._worker = worker

    def read_current_signal(self) -> Signal | None:
        return self._worker.last_signal

    async def ingest_tick(self, tick: TickEvent) -> Signal:
        return await self._worker.ingest_tick(tick)
