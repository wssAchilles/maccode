from __future__ import annotations

from typing import Any

from app.config import settings
from app.redis_worker import RedisMarketWorker


def build_worker_state(worker: RedisMarketWorker) -> dict[str, Any]:
    return {
        "started": worker.started,
        "market_ingest_mode": worker.market_ingest_mode,
        "market_loop_running": worker.market_loop_running,
        "execution_loop_running": worker.execution_loop_running,
        "redis_configured": worker.redis_configured,
        "market_stream_enabled": settings.market_stream_enabled,
        "market_stream_legacy_pubsub_fallback": settings.market_stream_legacy_pubsub_fallback,
        "event_stream_enabled": settings.event_stream_enabled,
        "event_stream_publish_legacy_pubsub": settings.event_stream_publish_legacy_pubsub,
        "market_stream_events": worker.market_stream_events,
        "market_stream_ack_failures": worker.market_stream_ack_failures,
        "market_stream_read_failures": worker.market_stream_read_failures,
        "market_stream_retry_attempts": worker.market_stream_retry_attempts,
        "market_stream_fallbacks": worker.market_stream_fallbacks,
        "market_stream_consecutive_failures": worker.market_stream_consecutive_failures,
        "last_market_stream_retry_backoff_ms": worker.last_market_stream_retry_backoff_ms,
        "last_market_stream_id": worker.last_market_stream_id,
        "market_stream_pending": worker.market_stream_pending,
        "market_stream_lag": worker.market_stream_lag,
        "market_stream_reclaim_attempts": worker.market_stream_reclaim_attempts,
        "market_stream_reclaimed": worker.market_stream_reclaimed,
        "market_stream_reclaim_failures": worker.market_stream_reclaim_failures,
        "market_stream_poisoned": worker.market_stream_poisoned,
        "last_market_stream_reclaim_at_ms": worker.last_market_stream_reclaim_at_ms,
        "last_market_stream_poison_id": worker.last_market_stream_poison_id,
    }
