from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Optional

from redis.asyncio import Redis

from app.config import settings
from app.firebase_publisher import FirebaseSignalPublisher
from app.order_client import MatchingOrderClient
from app.redis_worker.runtime_state import WorkerRuntimeState
from app.signal_engine_service import SignalEngineService
from app.supabase_publisher import SupabaseSignalPublisher
from app.worker_idempotency import WorkerIdempotencyService

if TYPE_CHECKING:
    from app.redis_worker.service import RedisMarketWorker


def initialize_worker_state(worker: RedisMarketWorker) -> None:
    worker._signal_application = None
    worker._redis = None
    worker._task = None
    worker._execution_task = None
    worker._started = False
    worker._runtime_state = WorkerRuntimeState()
    worker._signal_engine = SignalEngineService(
        fast_window=settings.fast_window,
        slow_window=settings.slow_window,
    )
    worker._firebase = FirebaseSignalPublisher()
    worker._supabase = SupabaseSignalPublisher()
    worker._matching = MatchingOrderClient()
    worker._idempotency = WorkerIdempotencyService(redis_getter=lambda: worker._redis)


RedisClient = Optional[Redis]
WorkerTask = Optional[asyncio.Task[None]]
