from __future__ import annotations

from typing import Any

from app.config import settings
from app.ports import RuntimeStatusPort


def build_worker_state(runtime_status: RuntimeStatusPort) -> dict[str, Any]:
    snapshot = runtime_status.runtime_snapshot()
    market_stream = snapshot.market_stream
    return {
        "started": snapshot.started,
        "market_ingest_mode": snapshot.market_ingest_mode,
        "market_loop_running": snapshot.market_loop_running,
        "execution_loop_running": snapshot.execution_loop_running,
        "redis_configured": snapshot.redis_configured,
        "market_stream_enabled": settings.market_stream_enabled,
        "market_stream_legacy_pubsub_fallback": settings.market_stream_legacy_pubsub_fallback,
        "event_stream_enabled": settings.event_stream_enabled,
        "event_stream_publish_legacy_pubsub": settings.event_stream_publish_legacy_pubsub,
        "market_stream_events": market_stream.events,
        "market_stream_ack_failures": market_stream.ack_failures,
        "market_stream_read_failures": market_stream.read_failures,
        "market_stream_retry_attempts": market_stream.retry_attempts,
        "market_stream_fallbacks": market_stream.fallbacks,
        "market_stream_consecutive_failures": market_stream.consecutive_failures,
        "last_market_stream_retry_backoff_ms": market_stream.last_retry_backoff_ms,
        "last_market_stream_id": market_stream.last_stream_id,
        "market_stream_pending": market_stream.pending,
        "market_stream_lag": market_stream.lag,
        "market_stream_reclaim_attempts": market_stream.reclaim_attempts,
        "market_stream_reclaimed": market_stream.reclaimed,
        "market_stream_reclaim_failures": market_stream.reclaim_failures,
        "market_stream_poisoned": market_stream.poisoned,
        "last_market_stream_reclaim_at_ms": market_stream.last_reclaim_at_ms,
        "last_market_stream_poison_id": market_stream.last_poison_id,
    }
