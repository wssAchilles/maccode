from __future__ import annotations

from time import monotonic
from typing import Any

from app.config import settings
from app.http import prometheus_escape
from app.redis_worker import RedisMarketWorker
from app.signal_store import SignalStore


def _worker_state(worker: RedisMarketWorker) -> dict[str, Any]:
    return {
        "started": worker.started,
        "market_ingest_mode": worker.market_ingest_mode,
        "market_loop_running": worker.market_loop_running,
        "execution_loop_running": worker.execution_loop_running,
        "redis_configured": worker.redis_configured,
        "market_stream_events": worker.market_stream_events,
        "market_stream_ack_failures": worker.market_stream_ack_failures,
        "market_stream_read_failures": worker.market_stream_read_failures,
        "market_stream_retry_attempts": worker.market_stream_retry_attempts,
        "market_stream_fallbacks": worker.market_stream_fallbacks,
        "market_stream_consecutive_failures": worker.market_stream_consecutive_failures,
        "last_market_stream_retry_backoff_ms": worker.last_market_stream_retry_backoff_ms,
        "last_market_stream_id": worker.last_market_stream_id,
    }


def _default_matching_health(enabled: bool) -> dict[str, Any]:
    return {
        "enabled": enabled,
        "reachable": False,
        "degraded": False,
        "status": "disabled" if not enabled else "unknown",
        "service": "matching-cpp",
        "version": "",
        "uptime_seconds": 0,
    }


def _default_matching_stats(enabled: bool) -> dict[str, Any]:
    return {
        "enabled": enabled,
        "degraded": False,
        "live_orders": 0,
        "trade_count": 0,
        "tracked_orders": 0,
        "rejected_orders": 0,
        "symbols": 0,
        "best_bid": None,
        "best_ask": None,
        "submit_order_requests_total": 0,
        "submit_order_errors_total": 0,
        "submit_order_rejections_total": 0,
        "submit_order_latency_p95_ms": 0.0,
        "submit_order_throughput_rps": 0.0,
        "trade_throughput_rps": 0.0,
        "reason": None,
    }


async def build_ready_content(
    worker: RedisMarketWorker,
    *,
    started_at: float,
    request_id: str,
) -> tuple[int, dict[str, Any]]:
    reasons: list[str] = []

    if not worker.redis_configured:
        reasons.append("redis_url_missing")
    if not worker.started:
        reasons.append("worker_not_started")
    if (
        settings.market_stream_enabled
        and not settings.market_stream_legacy_pubsub_fallback
        and worker.market_stream_fallbacks > 0
    ):
        reasons.append("market_stream_unstable")

    if settings.matching_enabled:
        matching = await worker.matching_client.health(request_id=request_id)
        if not matching.get("reachable", False):
            reasons.append("matching_unreachable")
        if bool(matching.get("degraded", False)):
            reasons.append("matching_degraded")
    else:
        matching = _default_matching_health(enabled=False)

    status_code = 200 if not reasons else 503
    return status_code, {
        "ready": status_code == 200,
        "service": settings.service_name,
        "uptime_seconds": int(max(monotonic() - started_at, 0.0)),
        "reasons": reasons,
        "worker": _worker_state(worker),
        "matching": matching,
        "request_id": request_id,
    }


async def build_metrics_lines(
    worker: RedisMarketWorker,
    signal_store: SignalStore,
    *,
    started_at: float,
    request_id: str,
) -> list[str]:
    uptime_seconds = int(max(monotonic() - started_at, 0.0))
    idempotency = worker.idempotency_snapshot()

    matching_status = "disabled"
    matching_reachable = 0
    matching_degraded = 0
    matching_uptime_seconds = 0
    if worker.matching_client.enabled:
        health = await worker.matching_client.health(request_id=request_id)
        matching_status = str(health.get("status", "unknown"))
        matching_reachable = 1 if bool(health.get("reachable", False)) else 0
        matching_degraded = 1 if bool(health.get("degraded", False)) else 0
        matching_uptime_seconds = int(health.get("uptime_seconds", 0))

    stores = signal_store.status()
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
        f"cerberus_strategy_worker_started {1 if worker.started else 0}",
        f"cerberus_strategy_worker_market_loop_running {1 if worker.market_loop_running else 0}",
        f"cerberus_strategy_worker_execution_loop_running {1 if worker.execution_loop_running else 0}",
        f"cerberus_strategy_worker_redis_configured {1 if worker.redis_configured else 0}",
        (
            "cerberus_strategy_market_ingest_mode"
            f'{{mode="{prometheus_escape(worker.market_ingest_mode)}"}} 1'
        ),
        f"cerberus_strategy_processed_ticks_total {worker.processed_ticks}",
        f"cerberus_strategy_market_stream_events_total {worker.market_stream_events}",
        f"cerberus_strategy_market_stream_ack_failures_total {worker.market_stream_ack_failures}",
        f"cerberus_strategy_market_stream_read_failures_total {worker.market_stream_read_failures}",
        f"cerberus_strategy_market_stream_retry_attempts_total {worker.market_stream_retry_attempts}",
        f"cerberus_strategy_market_stream_fallbacks_total {worker.market_stream_fallbacks}",
        f"cerberus_strategy_market_stream_consecutive_failures {worker.market_stream_consecutive_failures}",
        (
            "cerberus_strategy_market_stream_last_retry_backoff_ms "
            f"{worker.last_market_stream_retry_backoff_ms or 0}"
        ),
        f"cerberus_strategy_forwarded_executions_total {worker.forwarded_executions}",
        f"cerberus_strategy_last_execution_id {worker.last_execution_id}",
        f"cerberus_strategy_tracked_symbols {len(worker.tracked_symbols)}",
        f"cerberus_strategy_last_tick_timestamp_seconds {worker.last_tick_epoch_seconds or 0}",
        f"cerberus_strategy_last_error {1 if worker.last_error else 0}",
        f"cerberus_strategy_store_enabled{{store=\"firebase\"}} {1 if stores['firebase_enabled'] else 0}",
        f"cerberus_strategy_store_enabled{{store=\"supabase\"}} {1 if stores['supabase_enabled'] else 0}",
        f"cerberus_strategy_matching_enabled {1 if worker.matching_client.enabled else 0}",
        f"cerberus_strategy_matching_reachable {matching_reachable}",
        f"cerberus_strategy_matching_degraded {matching_degraded}",
        (
            "cerberus_strategy_matching_status"
            f'{{status="{prometheus_escape(matching_status)}"}} 1'
        ),
        f"cerberus_strategy_matching_uptime_seconds {matching_uptime_seconds}",
        f"cerberus_strategy_idempotency_redis_enabled {1 if idempotency['redis_enabled'] else 0}",
        f"cerberus_strategy_idempotency_signal_claim_attempts_total {idempotency['signal_claim_attempts']}",
        f"cerberus_strategy_idempotency_signal_conflicts_total {idempotency['signal_claim_conflicts']}",
        f"cerberus_strategy_idempotency_signal_rollbacks_total {idempotency['signal_claim_rollbacks']}",
        f"cerberus_strategy_idempotency_order_claim_attempts_total {idempotency['order_claim_attempts']}",
        f"cerberus_strategy_idempotency_order_conflicts_total {idempotency['order_claim_conflicts']}",
        f"cerberus_strategy_idempotency_order_rollbacks_total {idempotency['order_claim_rollbacks']}",
        f"cerberus_strategy_idempotency_redis_errors_total {idempotency['redis_errors']}",
    ]


async def build_persistence_status(
    worker: RedisMarketWorker,
    signal_store: SignalStore,
    *,
    request_id: str,
) -> dict[str, Any]:
    matching_health = _default_matching_health(enabled=worker.matching_client.enabled)
    matching_stats = _default_matching_stats(enabled=worker.matching_client.enabled)
    idempotency = worker.idempotency_snapshot()

    if worker.matching_client.enabled:
        try:
            matching_health = await worker.matching_client.health(request_id=request_id)
            matching_stats = await worker.matching_client.get_service_stats(request_id=request_id)
        except Exception as exc:
            matching_health = {
                **matching_health,
                "enabled": True,
                "degraded": True,
                "status": "error",
                "reason": str(exc),
            }

    return {
        "status": "ok",
        "worker": {
            "processed_ticks": worker.processed_ticks,
            "forwarded_executions": worker.forwarded_executions,
            "last_execution_id": worker.last_execution_id,
            "last_tick_at": worker.last_tick_at,
            "last_error": worker.last_error,
            "has_last_signal": worker.last_signal is not None,
            "tracked_symbols": worker.tracked_symbols,
            "idempotency": idempotency,
            **_worker_state(worker),
        },
        "matching": {
            "health": matching_health,
            "stats": matching_stats,
        },
        "stores": signal_store.status(),
    }
