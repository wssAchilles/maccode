from __future__ import annotations

from app.config import settings
from app.http import prometheus_escape
from app.ports import RuntimeStatusPort


def worker_runtime_metrics_lines(runtime_status: RuntimeStatusPort) -> list[str]:
    snapshot = runtime_status.runtime_snapshot()
    return [
        f"cerberus_strategy_worker_started {1 if snapshot.started else 0}",
        f"cerberus_strategy_worker_market_loop_running {1 if snapshot.market_loop_running else 0}",
        f"cerberus_strategy_worker_execution_loop_running {1 if snapshot.execution_loop_running else 0}",
        f"cerberus_strategy_worker_redis_configured {1 if snapshot.redis_configured else 0}",
        f"cerberus_strategy_market_stream_enabled {1 if settings.market_stream_enabled else 0}",
        (
            "cerberus_strategy_market_stream_legacy_pubsub_fallback_enabled "
            f"{1 if settings.market_stream_legacy_pubsub_fallback else 0}"
        ),
        f"cerberus_strategy_event_stream_enabled {1 if settings.event_stream_enabled else 0}",
        (
            "cerberus_strategy_event_stream_legacy_pubsub_publish_enabled "
            f"{1 if settings.event_stream_publish_legacy_pubsub else 0}"
        ),
        (
            "cerberus_strategy_market_ingest_mode"
            f'{{mode="{prometheus_escape(snapshot.market_ingest_mode)}"}} 1'
        ),
        f"cerberus_strategy_processed_ticks_total {snapshot.processed_ticks}",
        f"cerberus_strategy_forwarded_executions_total {snapshot.forwarded_executions}",
        f"cerberus_strategy_last_execution_id {snapshot.last_execution_id}",
        f"cerberus_strategy_tracked_symbols {len(snapshot.tracked_symbols)}",
        f"cerberus_strategy_last_tick_timestamp_seconds {snapshot.last_tick_epoch_seconds or 0}",
        f"cerberus_strategy_last_error {1 if snapshot.last_error else 0}",
    ]


def market_stream_metrics_lines(runtime_status: RuntimeStatusPort) -> list[str]:
    market_stream = runtime_status.runtime_snapshot().market_stream
    return [
        f"cerberus_strategy_market_stream_events_total {market_stream.events}",
        f"cerberus_strategy_market_stream_ack_failures_total {market_stream.ack_failures}",
        f"cerberus_strategy_market_stream_read_failures_total {market_stream.read_failures}",
        f"cerberus_strategy_market_stream_retry_attempts_total {market_stream.retry_attempts}",
        f"cerberus_strategy_market_stream_fallbacks_total {market_stream.fallbacks}",
        f"cerberus_strategy_market_stream_consecutive_failures {market_stream.consecutive_failures}",
        f"cerberus_strategy_market_stream_pending {market_stream.pending}",
        f"cerberus_strategy_market_stream_lag {market_stream.lag}",
        f"cerberus_strategy_market_stream_reclaim_attempts_total {market_stream.reclaim_attempts}",
        f"cerberus_strategy_market_stream_reclaimed_total {market_stream.reclaimed}",
        f"cerberus_strategy_market_stream_reclaim_failures_total {market_stream.reclaim_failures}",
        f"cerberus_strategy_market_stream_poisoned_total {market_stream.poisoned}",
        (
            "cerberus_strategy_market_stream_last_retry_backoff_ms "
            f"{market_stream.last_retry_backoff_ms or 0}"
        ),
        (
            "cerberus_strategy_market_stream_last_reclaim_at_ms "
            f"{market_stream.last_reclaim_at_ms or 0}"
        ),
    ]


def idempotency_metrics_lines(idempotency: dict[str, object]) -> list[str]:
    return [
        f"cerberus_strategy_idempotency_redis_enabled {1 if idempotency['redis_enabled'] else 0}",
        f"cerberus_strategy_idempotency_signal_claim_attempts_total {idempotency['signal_claim_attempts']}",
        f"cerberus_strategy_idempotency_signal_conflicts_total {idempotency['signal_claim_conflicts']}",
        f"cerberus_strategy_idempotency_signal_rollbacks_total {idempotency['signal_claim_rollbacks']}",
        f"cerberus_strategy_idempotency_order_claim_attempts_total {idempotency['order_claim_attempts']}",
        f"cerberus_strategy_idempotency_order_conflicts_total {idempotency['order_claim_conflicts']}",
        f"cerberus_strategy_idempotency_order_rollbacks_total {idempotency['order_claim_rollbacks']}",
        f"cerberus_strategy_idempotency_redis_errors_total {idempotency['redis_errors']}",
    ]
