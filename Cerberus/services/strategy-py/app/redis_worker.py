from __future__ import annotations

import asyncio
import contextlib
import logging
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Optional

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.config import settings
from app.engine import MovingAverageEngine
from app.firebase_publisher import FirebaseSignalPublisher
from app.order_client import MatchingOrderClient
from app.redis_worker_loops import (
    publish_signal_event,
    publish_matching_submission,
    run_execution_relay_loop,
    run_market_loop,
)
from app.schemas import Signal, TickEvent
from app.supabase_publisher import SupabaseSignalPublisher

logger = logging.getLogger(__name__)


class RedisMarketWorker:
    _IDEMPOTENCY_SCOPE_SIGNAL = "signal"
    _IDEMPOTENCY_SCOPE_ORDER = "order"

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
        self.market_ingest_mode: str = "starting"
        self.market_stream_events: int = 0
        self.market_stream_ack_failures: int = 0
        self.market_stream_read_failures: int = 0
        self.market_stream_retry_attempts: int = 0
        self.market_stream_fallbacks: int = 0
        self.market_stream_consecutive_failures: int = 0
        self.last_market_stream_retry_backoff_ms: int | None = None
        self.last_market_stream_id: str | None = None
        self.forwarded_executions: int = 0
        self.last_execution_id: int = 0
        self.last_tick_at: str | None = None
        self.last_tick_epoch_seconds: int | None = None
        self.last_error: str | None = None
        self.signal_claim_attempts: int = 0
        self.signal_claim_conflicts: int = 0
        self.signal_claim_rollbacks: int = 0
        self.order_claim_attempts: int = 0
        self.order_claim_conflicts: int = 0
        self.order_claim_rollbacks: int = 0
        self.idempotency_redis_errors: int = 0
        self._processed_signal_ids: OrderedDict[str, float] = OrderedDict()
        self._processed_order_ids: OrderedDict[str, float] = OrderedDict()

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
        self.market_ingest_mode = "starting"
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
        self.market_ingest_mode = "stopped"

    async def _run_market_loop(self) -> None:
        consecutive_failures = 0
        while True:
            try:
                await run_market_loop(self)
                consecutive_failures = 0
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                consecutive_failures += 1
                self.last_error = f"market loop: {exc}"
                delay_seconds = min(2 ** max(consecutive_failures - 1, 0), 15)
                logger.warning(
                    "market worker loop failed (attempt=%s, backoff=%ss): %s",
                    consecutive_failures,
                    delay_seconds,
                    exc,
                )
                await asyncio.sleep(delay_seconds)

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
        signal_id = self.build_signal_id(tick, signal)
        if not await self.claim_signal(signal_id):
            return signal

        try:
            self.last_signal = signal

            if self._redis is not None:
                await publish_signal_event(self, signal, tick, signal_id)
                await self._publish_matching_submission(signal, tick.price, signal_id)

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

    async def _publish_matching_submission(
        self, signal: Signal, tick_price: float, signal_id: str
    ) -> None:
        await publish_matching_submission(self, signal, tick_price, signal_id)

    async def _run_execution_relay_loop(self) -> None:
        await run_execution_relay_loop(self)

    def build_signal_id(self, tick: TickEvent, signal: Signal) -> str:
        event_time = tick.event_time.strip() or "0"
        return f"{signal.strategy_id}:{signal.symbol}:{event_time}:{signal.signal}"

    async def claim_signal(self, signal_id: str) -> bool:
        return await self._claim_idempotency_key(self._IDEMPOTENCY_SCOPE_SIGNAL, signal_id)

    async def release_signal_claim(self, signal_id: str) -> None:
        await self._release_idempotency_key(self._IDEMPOTENCY_SCOPE_SIGNAL, signal_id)

    async def claim_order(self, order_id: str) -> bool:
        return await self._claim_idempotency_key(self._IDEMPOTENCY_SCOPE_ORDER, order_id)

    async def release_order_claim(self, order_id: str) -> None:
        await self._release_idempotency_key(self._IDEMPOTENCY_SCOPE_ORDER, order_id)

    async def _claim_idempotency_key(self, scope: str, key: str) -> bool:
        normalized = key.strip()
        if not normalized:
            return True

        self._increment_claim_attempt(scope)
        cache = self._cache_for_scope(scope)
        if self._cache_contains(cache, normalized):
            self._increment_claim_conflict(scope)
            return False

        if self._redis is not None and settings.idempotency_store_redis_enabled:
            redis_key = self._redis_idempotency_key(scope, normalized)
            try:
                claimed = await self._redis.set(
                    redis_key,
                    "1",
                    nx=True,
                    ex=max(settings.signal_idempotency_ttl_seconds, 1),
                )
                if claimed:
                    self._mark_processed(cache, normalized)
                    return True
                self._mark_processed(cache, normalized)
                self._increment_claim_conflict(scope)
                return False
            except RedisError as exc:
                self.idempotency_redis_errors += 1
                logger.warning(
                    "redis idempotency claim failed (scope=%s, key=%s): %s",
                    scope,
                    normalized,
                    exc,
                )

        return self._claim_with_local_cache(cache, normalized)

    async def _release_idempotency_key(self, scope: str, key: str) -> None:
        normalized = key.strip()
        if not normalized:
            return

        if self._redis is not None and settings.idempotency_store_redis_enabled:
            redis_key = self._redis_idempotency_key(scope, normalized)
            try:
                await self._redis.delete(redis_key)
            except RedisError as exc:
                self.idempotency_redis_errors += 1
                logger.warning(
                    "redis idempotency release failed (scope=%s, key=%s): %s",
                    scope,
                    normalized,
                    exc,
                )

        self._cache_for_scope(scope).pop(normalized, None)
        self._increment_claim_rollback(scope)

    def _redis_idempotency_key(self, scope: str, key: str) -> str:
        prefix = settings.idempotency_redis_key_prefix.strip() or "cerberus:idempotency"
        return f"{prefix}:{scope}:{key}"

    def _cache_for_scope(self, scope: str) -> OrderedDict[str, float]:
        if scope == self._IDEMPOTENCY_SCOPE_ORDER:
            return self._processed_order_ids
        return self._processed_signal_ids

    def _cache_contains(self, cache: OrderedDict[str, float], key: str) -> bool:
        self._cleanup_expired(cache)
        return key in cache

    def _claim_with_local_cache(self, cache: OrderedDict[str, float], key: str) -> bool:
        if self._cache_contains(cache, key):
            if cache is self._processed_order_ids:
                self.order_claim_conflicts += 1
            else:
                self.signal_claim_conflicts += 1
            return False
        self._mark_processed(cache, key)
        return True

    def _increment_claim_attempt(self, scope: str) -> None:
        if scope == self._IDEMPOTENCY_SCOPE_ORDER:
            self.order_claim_attempts += 1
            return
        self.signal_claim_attempts += 1

    def _increment_claim_conflict(self, scope: str) -> None:
        if scope == self._IDEMPOTENCY_SCOPE_ORDER:
            self.order_claim_conflicts += 1
            return
        self.signal_claim_conflicts += 1

    def _increment_claim_rollback(self, scope: str) -> None:
        if scope == self._IDEMPOTENCY_SCOPE_ORDER:
            self.order_claim_rollbacks += 1
            return
        self.signal_claim_rollbacks += 1

    def idempotency_snapshot(self) -> dict[str, int | bool]:
        return {
            "redis_enabled": self._redis is not None and settings.idempotency_store_redis_enabled,
            "signal_claim_attempts": self.signal_claim_attempts,
            "signal_claim_conflicts": self.signal_claim_conflicts,
            "signal_claim_rollbacks": self.signal_claim_rollbacks,
            "order_claim_attempts": self.order_claim_attempts,
            "order_claim_conflicts": self.order_claim_conflicts,
            "order_claim_rollbacks": self.order_claim_rollbacks,
            "redis_errors": self.idempotency_redis_errors,
        }

    def _mark_processed(self, cache: OrderedDict[str, float], key: str) -> None:
        now = datetime.now(timezone.utc).timestamp()
        cache[key] = now
        cache.move_to_end(key)
        self._cleanup_expired(cache)
        while len(cache) > max(settings.idempotency_max_entries, 1):
            cache.popitem(last=False)

    def _cleanup_expired(self, cache: OrderedDict[str, float]) -> None:
        now = datetime.now(timezone.utc).timestamp()
        ttl = max(settings.signal_idempotency_ttl_seconds, 1)
        to_remove = [key for key, ts in cache.items() if now - ts > ttl]
        for key in to_remove:
            cache.pop(key, None)
