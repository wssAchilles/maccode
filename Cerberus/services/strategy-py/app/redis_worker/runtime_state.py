from __future__ import annotations

from dataclasses import dataclass, field

from app.schemas import Signal


@dataclass(slots=True)
class MarketStreamRuntimeState:
    events: int = 0
    ack_failures: int = 0
    read_failures: int = 0
    retry_attempts: int = 0
    fallbacks: int = 0
    consecutive_failures: int = 0
    last_retry_backoff_ms: int | None = None
    last_stream_id: str | None = None
    pending: int = 0
    lag: int = 0
    reclaim_attempts: int = 0
    reclaimed: int = 0
    reclaim_failures: int = 0
    poisoned: int = 0
    last_reclaim_at_ms: int | None = None
    last_poison_id: str | None = None


@dataclass(slots=True)
class WorkerRuntimeState:
    last_signal: Signal | None = None
    processed_ticks: int = 0
    market_ingest_mode: str = "starting"
    forwarded_executions: int = 0
    last_execution_id: int = 0
    last_tick_at: str | None = None
    last_tick_epoch_seconds: int | None = None
    last_error: str | None = None
    market_stream: MarketStreamRuntimeState = field(default_factory=MarketStreamRuntimeState)


@dataclass(frozen=True, slots=True)
class MarketStreamRuntimeSnapshot:
    events: int
    ack_failures: int
    read_failures: int
    retry_attempts: int
    fallbacks: int
    consecutive_failures: int
    last_retry_backoff_ms: int | None
    last_stream_id: str | None
    pending: int
    lag: int
    reclaim_attempts: int
    reclaimed: int
    reclaim_failures: int
    poisoned: int
    last_reclaim_at_ms: int | None
    last_poison_id: str | None


@dataclass(frozen=True, slots=True)
class WorkerRuntimeSnapshot:
    started: bool
    market_loop_running: bool
    execution_loop_running: bool
    redis_configured: bool
    tracked_symbols: tuple[str, ...]
    last_signal: Signal | None
    processed_ticks: int
    market_ingest_mode: str
    forwarded_executions: int
    last_execution_id: int
    last_tick_at: str | None
    last_tick_epoch_seconds: int | None
    last_error: str | None
    market_stream: MarketStreamRuntimeSnapshot

