from __future__ import annotations

from typing import TYPE_CHECKING

from app.config import settings
from app.order_client import MatchingOrderClient
from app.redis_worker.runtime_state import (
    MarketStreamRuntimeSnapshot,
    WorkerRuntimeSnapshot,
)
from app.schemas import Signal, TickEvent
from app.worker_lifecycle import run_market_supervisor_loop, start_worker, stop_worker

from .bootstrap import initialize_worker_state
from .ingest import ingest_tick, record_tick_processed

if TYPE_CHECKING:
    from app.application import SignalApplicationService
    from app.firebase_publisher import FirebaseSignalPublisher
    from app.supabase_publisher import SupabaseSignalPublisher
    from redis.asyncio import Redis


class RedisMarketWorker:
    def __init__(self) -> None:
        initialize_worker_state(self)

    @property
    def matching_client(self) -> MatchingOrderClient:
        return self._matching

    @property
    def redis_client(self) -> Redis | None:
        return self._redis

    @property
    def last_signal(self) -> Signal | None:
        return self._runtime_state.last_signal

    @last_signal.setter
    def last_signal(self, value: Signal | None) -> None:
        self._runtime_state.last_signal = value

    @property
    def processed_ticks(self) -> int:
        return self._runtime_state.processed_ticks

    @property
    def last_decision(self):
        return self._runtime_state.last_decision

    @property
    def market_ingest_mode(self) -> str:
        return self._runtime_state.market_ingest_mode

    @property
    def market_stream_events(self) -> int:
        return self._runtime_state.market_stream.events

    @property
    def market_stream_ack_failures(self) -> int:
        return self._runtime_state.market_stream.ack_failures

    @property
    def market_stream_read_failures(self) -> int:
        return self._runtime_state.market_stream.read_failures

    @property
    def market_stream_retry_attempts(self) -> int:
        return self._runtime_state.market_stream.retry_attempts

    @property
    def market_stream_fallbacks(self) -> int:
        return self._runtime_state.market_stream.fallbacks

    @property
    def market_stream_consecutive_failures(self) -> int:
        return self._runtime_state.market_stream.consecutive_failures

    @property
    def last_market_stream_retry_backoff_ms(self) -> int | None:
        return self._runtime_state.market_stream.last_retry_backoff_ms

    @property
    def last_market_stream_id(self) -> str | None:
        return self._runtime_state.market_stream.last_stream_id

    @property
    def market_stream_pending(self) -> int:
        return self._runtime_state.market_stream.pending

    @property
    def market_stream_lag(self) -> int:
        return self._runtime_state.market_stream.lag

    @property
    def market_stream_reclaim_attempts(self) -> int:
        return self._runtime_state.market_stream.reclaim_attempts

    @property
    def market_stream_reclaimed(self) -> int:
        return self._runtime_state.market_stream.reclaimed

    @property
    def market_stream_reclaim_failures(self) -> int:
        return self._runtime_state.market_stream.reclaim_failures

    @property
    def market_stream_poisoned(self) -> int:
        return self._runtime_state.market_stream.poisoned

    @property
    def last_market_stream_reclaim_at_ms(self) -> int | None:
        return self._runtime_state.market_stream.last_reclaim_at_ms

    @property
    def last_market_stream_poison_id(self) -> str | None:
        return self._runtime_state.market_stream.last_poison_id

    @property
    def forwarded_executions(self) -> int:
        return self._runtime_state.forwarded_executions

    @property
    def last_execution_id(self) -> int:
        return self._runtime_state.last_execution_id

    @property
    def last_tick_at(self) -> str | None:
        return self._runtime_state.last_tick_at

    @property
    def last_tick_epoch_seconds(self) -> int | None:
        return self._runtime_state.last_tick_epoch_seconds

    @property
    def last_error(self) -> str | None:
        return self._runtime_state.last_error

    @last_error.setter
    def last_error(self, value: str | None) -> None:
        self._runtime_state.last_error = value

    @property
    def firebase_publisher(self) -> FirebaseSignalPublisher:
        return self._firebase

    @property
    def supabase_publisher(self) -> SupabaseSignalPublisher:
        return self._supabase

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
        if self._signal_application is not None:
            decision = await self._signal_application.ingest_tick(tick)
            return decision.signal
        return await ingest_tick(self, tick)

    async def _run_execution_relay_loop(self) -> None:
        from app.event_runtime import run_execution_relay_loop

        await run_execution_relay_loop(self)

    def attach_signal_application(self, application: SignalApplicationService) -> None:
        self._signal_application = application

    def evaluate_tick(self, tick: TickEvent) -> tuple[Signal, str]:
        return self._signal_engine.evaluate_tick(tick)

    def build_signal_id(self, tick: TickEvent, signal: Signal) -> str:
        return self._signal_engine.build_signal_id(tick, signal)

    def store_current_signal(self, signal: Signal) -> None:
        self._runtime_state.last_signal = signal

    def store_current_decision(self, decision) -> None:
        self._runtime_state.last_decision = decision

    def record_tick_processed(self) -> None:
        record_tick_processed(self)

    def set_last_error(self, message: str) -> None:
        self._runtime_state.last_error = message

    def set_market_ingest_mode(self, mode: str) -> None:
        self._runtime_state.market_ingest_mode = mode

    def mark_market_stream_fallback(self) -> None:
        self._runtime_state.market_stream.fallbacks += 1

    def mark_market_stream_event_processed(self, stream_id: str) -> None:
        self._runtime_state.market_stream.events += 1
        self._runtime_state.market_stream.last_stream_id = stream_id

    def mark_market_stream_reclaim_attempt(self, when_ms: int) -> None:
        self._runtime_state.market_stream.reclaim_attempts += 1
        self._runtime_state.market_stream.last_reclaim_at_ms = when_ms

    def mark_market_stream_reclaimed(self, count: int) -> None:
        self._runtime_state.market_stream.reclaimed += count

    def mark_market_stream_poisoned(self, stream_id: str) -> None:
        self._runtime_state.market_stream.poisoned += 1
        self._runtime_state.market_stream.last_poison_id = stream_id

    def update_market_stream_backlog(self, *, pending: int, lag: int) -> None:
        self._runtime_state.market_stream.pending = pending
        self._runtime_state.market_stream.lag = lag

    def increment_market_stream_read_failures(self) -> None:
        self._runtime_state.market_stream.read_failures += 1

    def increment_market_stream_ack_failures(self) -> None:
        self._runtime_state.market_stream.ack_failures += 1

    def increment_market_stream_reclaim_failures(self) -> None:
        self._runtime_state.market_stream.reclaim_failures += 1

    def reset_market_stream_retry_state(self) -> None:
        self._runtime_state.market_stream.consecutive_failures = 0
        self._runtime_state.market_stream.last_retry_backoff_ms = None

    def record_market_stream_retry(
        self,
        *,
        consecutive_failures: int,
        backoff_ms: int,
        message: str,
    ) -> None:
        self._runtime_state.market_stream.retry_attempts += 1
        self._runtime_state.market_stream.consecutive_failures = consecutive_failures
        self._runtime_state.market_stream.last_retry_backoff_ms = backoff_ms
        self._runtime_state.last_error = message

    def increment_forwarded_executions(self, count: int) -> None:
        self._runtime_state.forwarded_executions += count

    def update_last_execution_id(self, execution_id: int) -> None:
        self._runtime_state.last_execution_id = execution_id

    def runtime_snapshot(self) -> WorkerRuntimeSnapshot:
        state = self._runtime_state
        market_stream = state.market_stream
        return WorkerRuntimeSnapshot(
            started=self.started,
            market_loop_running=self.market_loop_running,
            execution_loop_running=self.execution_loop_running,
            redis_configured=self.redis_configured,
            tracked_symbols=tuple(self.tracked_symbols),
            last_signal=state.last_signal,
            processed_ticks=state.processed_ticks,
            market_ingest_mode=state.market_ingest_mode,
            forwarded_executions=state.forwarded_executions,
            last_execution_id=state.last_execution_id,
            last_tick_at=state.last_tick_at,
            last_tick_epoch_seconds=state.last_tick_epoch_seconds,
            last_error=state.last_error,
            market_stream=MarketStreamRuntimeSnapshot(
                events=market_stream.events,
                ack_failures=market_stream.ack_failures,
                read_failures=market_stream.read_failures,
                retry_attempts=market_stream.retry_attempts,
                fallbacks=market_stream.fallbacks,
                consecutive_failures=market_stream.consecutive_failures,
                last_retry_backoff_ms=market_stream.last_retry_backoff_ms,
                last_stream_id=market_stream.last_stream_id,
                pending=market_stream.pending,
                lag=market_stream.lag,
                reclaim_attempts=market_stream.reclaim_attempts,
                reclaimed=market_stream.reclaimed,
                reclaim_failures=market_stream.reclaim_failures,
                poisoned=market_stream.poisoned,
                last_reclaim_at_ms=market_stream.last_reclaim_at_ms,
                last_poison_id=market_stream.last_poison_id,
            ),
        )

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
