from __future__ import annotations

from app.config import settings
from app.http import prometheus_escape
from app.redis_worker import RedisMarketWorker


def worker_runtime_metrics_lines(worker: RedisMarketWorker) -> list[str]:
    return [
        f"cerberus_strategy_worker_started {1 if worker.started else 0}",
        f"cerberus_strategy_worker_market_loop_running {1 if worker.market_loop_running else 0}",
        f"cerberus_strategy_worker_execution_loop_running {1 if worker.execution_loop_running else 0}",
        f"cerberus_strategy_worker_redis_configured {1 if worker.redis_configured else 0}",
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
            f'{{mode="{prometheus_escape(worker.market_ingest_mode)}"}} 1'
        ),
        f"cerberus_strategy_processed_ticks_total {worker.processed_ticks}",
        f"cerberus_strategy_forwarded_executions_total {worker.forwarded_executions}",
        f"cerberus_strategy_last_execution_id {worker.last_execution_id}",
        f"cerberus_strategy_tracked_symbols {len(worker.tracked_symbols)}",
        f"cerberus_strategy_last_tick_timestamp_seconds {worker.last_tick_epoch_seconds or 0}",
        f"cerberus_strategy_last_error {1 if worker.last_error else 0}",
    ]


def market_stream_metrics_lines(worker: RedisMarketWorker) -> list[str]:
    return [
        f"cerberus_strategy_market_stream_events_total {worker.market_stream_events}",
        f"cerberus_strategy_market_stream_ack_failures_total {worker.market_stream_ack_failures}",
        f"cerberus_strategy_market_stream_read_failures_total {worker.market_stream_read_failures}",
        f"cerberus_strategy_market_stream_retry_attempts_total {worker.market_stream_retry_attempts}",
        f"cerberus_strategy_market_stream_fallbacks_total {worker.market_stream_fallbacks}",
        f"cerberus_strategy_market_stream_consecutive_failures {worker.market_stream_consecutive_failures}",
        f"cerberus_strategy_market_stream_pending {worker.market_stream_pending}",
        f"cerberus_strategy_market_stream_lag {worker.market_stream_lag}",
        f"cerberus_strategy_market_stream_reclaim_attempts_total {worker.market_stream_reclaim_attempts}",
        f"cerberus_strategy_market_stream_reclaimed_total {worker.market_stream_reclaimed}",
        f"cerberus_strategy_market_stream_reclaim_failures_total {worker.market_stream_reclaim_failures}",
        f"cerberus_strategy_market_stream_poisoned_total {worker.market_stream_poisoned}",
        (
            "cerberus_strategy_market_stream_last_retry_backoff_ms "
            f"{worker.last_market_stream_retry_backoff_ms or 0}"
        ),
        (
            "cerberus_strategy_market_stream_last_reclaim_at_ms "
            f"{worker.last_market_stream_reclaim_at_ms or 0}"
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
