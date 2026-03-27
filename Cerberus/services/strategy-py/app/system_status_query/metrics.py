from __future__ import annotations

from dataclasses import dataclass
from time import monotonic

from app.config import settings
from app.http import prometheus_escape
from app.ports import MatchingObservabilityPort, RuntimeStatusPort, StoreStatusPort
from app.schemas import MatchingStatsView
from app.system_status_query.persistence import PersistenceStoresPayload


@dataclass(frozen=True)
class MatchingMetricsContext:
    enabled: int
    status: str
    reachable: int
    degraded: int
    uptime_seconds: int
    stats: MatchingStatsView


async def build_matching_metrics_context(
    matching_observability: MatchingObservabilityPort,
    *,
    request_id: str,
) -> MatchingMetricsContext:
    snapshot = await matching_observability.collect_snapshot(request_id=request_id)
    health = snapshot.health
    return MatchingMetricsContext(
        enabled=1 if health.enabled else 0,
        status=health.status,
        reachable=1 if health.reachable else 0,
        degraded=1 if health.degraded else 0,
        uptime_seconds=health.uptime_seconds,
        stats=snapshot.stats,
    )


def base_metrics_lines(uptime_seconds: int) -> list[str]:
    return [
        "# HELP cerberus_strategy_up Strategy process health.",
        "# TYPE cerberus_strategy_up gauge",
        "cerberus_strategy_up 1",
        (
            "cerberus_strategy_build_info"
            f'{{service="{prometheus_escape(settings.service_name)}",'
            f'version="{prometheus_escape(settings.service_version)}"}} 1'
        ),
        f"cerberus_strategy_uptime_seconds {uptime_seconds}",
    ]


def stores_metrics_lines(stores: PersistenceStoresPayload) -> list[str]:
    return [
        f"cerberus_strategy_store_enabled{{store=\"firebase\"}} {1 if stores.firebase_enabled else 0}",
        f"cerberus_strategy_store_enabled{{store=\"supabase\"}} {1 if stores.supabase_enabled else 0}",
    ]


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


def matching_metrics_lines(context: MatchingMetricsContext) -> list[str]:
    stats = context.stats
    return [
        f"cerberus_strategy_matching_enabled {context.enabled}",
        f"cerberus_strategy_matching_reachable {context.reachable}",
        f"cerberus_strategy_matching_degraded {context.degraded}",
        (
            "cerberus_strategy_matching_status"
            f'{{status="{prometheus_escape(context.status)}"}} 1'
        ),
        f"cerberus_strategy_matching_uptime_seconds {context.uptime_seconds}",
        (
            "cerberus_strategy_matching_submit_order_latency_p95_ms "
            f"{float(stats.submit_order_latency_p95_ms)}"
        ),
        (
            "cerberus_strategy_matching_submit_order_throughput_rps "
            f"{float(stats.submit_order_throughput_rps)}"
        ),
        (
            "cerberus_strategy_matching_trade_throughput_rps "
            f"{float(stats.trade_throughput_rps)}"
        ),
        (
            "cerberus_strategy_matching_inflight_requests "
            f"{int(stats.inflight_requests)}"
        ),
        (
            "cerberus_strategy_matching_inflight_requests_peak "
            f"{int(stats.inflight_requests_peak)}"
        ),
        (
            "cerberus_strategy_matching_max_inflight_requests "
            f"{int(stats.max_inflight_requests)}"
        ),
        (
            "cerberus_strategy_matching_backpressure_waits_total "
            f"{int(stats.backpressure_waits_total)}"
        ),
        (
            "cerberus_strategy_matching_backpressure_rejections_total "
            f"{int(stats.backpressure_rejections_total)}"
        ),
        (
            "cerberus_strategy_matching_backpressure_wait_timeouts_total "
            f"{int(stats.backpressure_wait_timeouts_total)}"
        ),
        (
            "cerberus_strategy_matching_backpressure_wait_ms_total "
            f"{int(stats.backpressure_wait_ms_total)}"
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


async def build_metrics_lines(
    runtime_status: RuntimeStatusPort,
    signal_store_status: StoreStatusPort,
    matching_observability: MatchingObservabilityPort,
    *,
    started_at: float,
    request_id: str,
) -> list[str]:
    uptime_seconds = int(max(monotonic() - started_at, 0.0))
    idempotency = runtime_status.idempotency_snapshot()
    stores = signal_store_status.status()
    matching = await build_matching_metrics_context(
        matching_observability,
        request_id=request_id,
    )

    lines: list[str] = []
    lines.extend(base_metrics_lines(uptime_seconds))
    lines.extend(worker_runtime_metrics_lines(runtime_status))
    lines.extend(market_stream_metrics_lines(runtime_status))
    lines.extend(stores_metrics_lines(stores))
    lines.extend(matching_metrics_lines(matching))
    lines.extend(idempotency_metrics_lines(idempotency))
    return lines
