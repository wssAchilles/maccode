from __future__ import annotations

from app.event_runtime import publish_signal_and_matching_submission
from app.redis_worker import RedisMarketWorker
from app.schemas import Signal, TickEvent


class WorkerSignalRuntimeAdapter:
    def __init__(self, worker: RedisMarketWorker) -> None:
        self._worker = worker

    def read_current_signal(self) -> Signal | None:
        return self._worker.last_signal

    def evaluate_tick(self, tick: TickEvent) -> tuple[Signal, str]:
        return self._worker.evaluate_tick(tick)

    def build_signal_id(self, tick: TickEvent, signal: Signal) -> str:
        return self._worker.build_signal_id(tick, signal)

    def store_current_signal(self, signal: Signal) -> None:
        self._worker.store_current_signal(signal)

    def record_tick_processed(self) -> None:
        self._worker.record_tick_processed()


class WorkerSignalClaimsAdapter:
    def __init__(self, worker: RedisMarketWorker) -> None:
        self._worker = worker

    async def claim_signal(self, signal_id: str) -> bool:
        return await self._worker.claim_signal(signal_id)

    async def release_signal_claim(self, signal_id: str) -> None:
        await self._worker.release_signal_claim(signal_id)


class WorkerSignalEventFlowAdapter:
    def __init__(self, worker: RedisMarketWorker) -> None:
        self._worker = worker

    async def publish_signal_flow(
        self,
        signal: Signal,
        tick: TickEvent,
        signal_id: str,
    ) -> None:
        await publish_signal_and_matching_submission(
            self._worker,
            signal,
            tick,
            signal_id,
        )
