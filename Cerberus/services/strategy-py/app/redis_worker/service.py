from __future__ import annotations

from app.config import settings
from app.order_client import MatchingOrderClient
from app.schemas import Signal, TickEvent
from app.worker_lifecycle import run_market_supervisor_loop, start_worker, stop_worker

from .bootstrap import initialize_worker_state
from .ingest import ingest_tick


class RedisMarketWorker:
    def __init__(self) -> None:
        initialize_worker_state(self)

    @property
    def matching_client(self) -> MatchingOrderClient:
        return self._matching

    @property
    def tracked_symbols(self) -> list[str]:
        return self._signal_engine.tracked_symbols

    @property
    def started(self) -> bool:
        return self._started

    @property
    def market_loop_running(self) -> bool:
        return self._task is not None and not self._task.done()

    @property
    def execution_loop_running(self) -> bool:
        return self._execution_task is not None and not self._execution_task.done()

    @property
    def redis_configured(self) -> bool:
        return bool(settings.redis_url.strip())

    async def start(self) -> None:
        await start_worker(self)

    async def stop(self) -> None:
        await stop_worker(self)

    async def _run_market_loop(self) -> None:
        await run_market_supervisor_loop(self)

    async def ingest_tick(self, tick: TickEvent) -> Signal:
        return await ingest_tick(self, tick)

    async def _run_execution_relay_loop(self) -> None:
        from app.event_runtime import run_execution_relay_loop

        await run_execution_relay_loop(self)

    def build_signal_id(self, tick: TickEvent, signal: Signal) -> str:
        return self._signal_engine.build_signal_id(tick, signal)

    async def claim_signal(self, signal_id: str) -> bool:
        return await self._idempotency.claim_signal(signal_id)

    async def release_signal_claim(self, signal_id: str) -> None:
        await self._idempotency.release_signal(signal_id)

    async def claim_order(self, order_id: str) -> bool:
        return await self._idempotency.claim_order(order_id)

    async def release_order_claim(self, order_id: str) -> None:
        await self._idempotency.release_order(order_id)

    def idempotency_snapshot(self) -> dict[str, int | bool]:
        return self._idempotency.snapshot()
