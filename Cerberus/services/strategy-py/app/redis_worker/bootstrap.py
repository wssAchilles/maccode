from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Optional

from redis.asyncio import Redis

from app.config import settings
from app.firebase_publisher import FirebaseSignalPublisher
from app.order_client import MatchingOrderClient
from app.signal_engine_service import SignalEngineService
from app.supabase_publisher import SupabaseSignalPublisher
from app.worker_idempotency import WorkerIdempotencyService

if TYPE_CHECKING:
    from app.redis_worker.service import RedisMarketWorker


def initialize_worker_state(worker: RedisMarketWorker) -> None:
    worker._redis = None
    worker._task = None
    worker._execution_task = None
    worker._started = False
    worker._signal_engine = SignalEngineService(
        fast_window=settings.fast_window,
        slow_window=settings.slow_window,
    )
    worker._firebase = FirebaseSignalPublisher()
    worker._supabase = SupabaseSignalPublisher()
    worker._matching = MatchingOrderClient()
    worker.last_signal = None
    worker.processed_ticks = 0
    worker.market_ingest_mode = "starting"
    worker.market_stream_events = 0
    worker.market_stream_ack_failures = 0
    worker.market_stream_read_failures = 0
    worker.market_stream_retry_attempts = 0
    worker.market_stream_fallbacks = 0
    worker.market_stream_consecutive_failures = 0
    worker.last_market_stream_retry_backoff_ms = None
    worker.last_market_stream_id = None
    worker.market_stream_pending = 0
    worker.market_stream_lag = 0
    worker.market_stream_reclaim_attempts = 0
    worker.market_stream_reclaimed = 0
    worker.market_stream_reclaim_failures = 0
    worker.market_stream_poisoned = 0
    worker.last_market_stream_reclaim_at_ms = None
    worker.last_market_stream_poison_id = None
    worker.forwarded_executions = 0
    worker.last_execution_id = 0
    worker.last_tick_at = None
    worker.last_tick_epoch_seconds = None
    worker.last_error = None
    worker._idempotency = WorkerIdempotencyService(redis_getter=lambda: worker._redis)


RedisClient = Optional[Redis]
WorkerTask = Optional[asyncio.Task[None]]
