from __future__ import annotations

import asyncio
import contextlib
import logging
from datetime import datetime, timezone
from typing import Optional

from redis.asyncio import Redis

from app.config import settings
from app.engine import MovingAverageEngine
from app.firebase_publisher import FirebaseSignalPublisher
from app.order_client import MatchingOrderClient
from app.redis_worker_loops import (
    publish_matching_submission,
    run_execution_relay_loop,
    run_market_loop,
)
from app.schemas import Signal, TickEvent
from app.supabase_publisher import SupabaseSignalPublisher

logger = logging.getLogger(__name__)


class RedisMarketWorker:
    def __init__(self) -> None:
        self._redis: Optional[Redis] = None
        self._task: Optional[asyncio.Task[None]] = None
        self._execution_task: Optional[asyncio.Task[None]] = None
        self._started: bool = False
        self._engines: dict[str, MovingAverageEngine] = {}
        self._firebase = FirebaseSignalPublisher()
        self._supabase = SupabaseSignalPublisher()
        self._matching = MatchingOrderClient()
        self.last_signal: Optional[Signal] = None
        self.processed_ticks: int = 0
        self.forwarded_executions: int = 0
        self.last_execution_id: int = 0
        self.last_tick_at: str | None = None
        self.last_tick_epoch_seconds: int | None = None
        self.last_error: str | None = None

    @property
    def matching_client(self) -> MatchingOrderClient:
        return self._matching

    @property
    def tracked_symbols(self) -> list[str]:
        return sorted(self._engines.keys())

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
        self._started = True
        if not settings.redis_url.strip():
            logger.warning("REDIS_URL is empty; strategy worker disabled")
            return

        self._redis = Redis.from_url(settings.redis_url, decode_responses=True)
        self._task = asyncio.create_task(self._run_market_loop(), name="redis-market-worker")
        if self._matching.enabled:
            self._execution_task = asyncio.create_task(
                self._run_execution_relay_loop(),
                name="matching-execution-relay",
            )

    async def stop(self) -> None:
        if self._execution_task:
            self._execution_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._execution_task

        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task

        if self._redis:
            await self._redis.aclose()

        await self._supabase.aclose()
        await self._matching.aclose()
        self._started = False

    async def _run_market_loop(self) -> None:
        await run_market_loop(self)

    async def ingest_tick(self, tick: TickEvent) -> Signal:
        engine = self._engines.get(tick.symbol)
        if engine is None:
            engine = MovingAverageEngine(
                fast_window=settings.fast_window,
                slow_window=settings.slow_window,
            )
            self._engines[tick.symbol] = engine

        result = engine.add_price(tick.price)
        signal = Signal(
            strategy_id="default",
            symbol=tick.symbol,
            signal=result.signal,
            confidence=result.confidence,
        )
        self.last_signal = signal

        if self._redis is not None:
            await self._redis.publish(settings.signal_channel, signal.model_dump_json())
            await self._publish_matching_submission(signal, tick.price)

        await self._firebase.publish_signal(signal)
        await self._supabase.publish_signal(signal)

        self.processed_ticks += 1
        now = datetime.now(timezone.utc)
        self.last_tick_at = now.isoformat()
        self.last_tick_epoch_seconds = int(now.timestamp())
        self.last_error = None
        return signal

    async def _publish_matching_submission(self, signal: Signal, tick_price: float) -> None:
        await publish_matching_submission(self, signal, tick_price)

    async def _run_execution_relay_loop(self) -> None:
        await run_execution_relay_loop(self)
