from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from redis.asyncio import Redis

from app.config import settings
from app.event_runtime import (
    publish_signal_and_matching_submission,
    run_execution_relay_loop,
)
from app.firebase_publisher import FirebaseSignalPublisher
from app.order_client import MatchingOrderClient
from app.schemas import Signal, TickEvent
from app.signal_engine_service import SignalEngineService
from app.supabase_publisher import SupabaseSignalPublisher
from app.worker_lifecycle import run_market_supervisor_loop, start_worker, stop_worker
from app.worker_idempotency import WorkerIdempotencyService

logger = logging.getLogger(__name__)


class RedisMarketWorker:
    def __init__(self) -> None:
        self._redis: Optional[Redis] = None
        self._task: Optional[asyncio.Task[None]] = None
        self._execution_task: Optional[asyncio.Task[None]] = None
        self._started: bool = False
        self._signal_engine = SignalEngineService(
            fast_window=settings.fast_window,
            slow_window=settings.slow_window,
        )
        self._firebase = FirebaseSignalPublisher()
        self._supabase = SupabaseSignalPublisher()
        self._matching = MatchingOrderClient()
        self.last_signal: Optional[Signal] = None
        self.processed_ticks: int = 0
        self.market_ingest_mode: str = "starting"
        self.market_stream_events: int = 0
        self.market_stream_ack_failures: int = 0
        self.market_stream_read_failures: int = 0
        self.market_stream_retry_attempts: int = 0
        self.market_stream_fallbacks: int = 0
        self.market_stream_consecutive_failures: int = 0
        self.last_market_stream_retry_backoff_ms: int | None = None
        self.last_market_stream_id: str | None = None
        self.market_stream_pending: int = 0
        self.market_stream_lag: int = 0
        self.market_stream_reclaim_attempts: int = 0
        self.market_stream_reclaimed: int = 0
        self.market_stream_reclaim_failures: int = 0
        self.market_stream_poisoned: int = 0
        self.last_market_stream_reclaim_at_ms: int | None = None
        self.last_market_stream_poison_id: str | None = None
        self.forwarded_executions: int = 0
        self.last_execution_id: int = 0
        self.last_tick_at: str | None = None
        self.last_tick_epoch_seconds: int | None = None
        self.last_error: str | None = None
        self._idempotency = WorkerIdempotencyService(redis_getter=lambda: self._redis)

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
        signal, signal_id = self._signal_engine.evaluate_tick(tick)
        if not await self.claim_signal(signal_id):
            return signal

        try:
            self.last_signal = signal

            if self._redis is not None:
                await publish_signal_and_matching_submission(self, signal, tick, signal_id)

            await self._firebase.publish_signal(signal)
            await self._supabase.publish_signal(signal)
        except Exception:
            await self.release_signal_claim(signal_id)
            raise

        self.processed_ticks += 1
        now = datetime.now(timezone.utc)
        self.last_tick_at = now.isoformat()
        self.last_tick_epoch_seconds = int(now.timestamp())
        self.last_error = None
        return signal

    async def _run_execution_relay_loop(self) -> None:
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
