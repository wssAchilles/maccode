from __future__ import annotations

from dataclasses import dataclass

from app.ports import MatchingGatewayPort
from app.schemas import MatchingHealthView, MatchingStatsView


@dataclass(frozen=True, slots=True)
class MatchingSnapshot:
    health: MatchingHealthView
    stats: MatchingStatsView


def default_matching_health(enabled: bool) -> MatchingHealthView:
    return MatchingHealthView(
        enabled=enabled,
        reachable=False,
        degraded=False,
        degraded_reason=None,
        status="disabled" if not enabled else "unknown",
        service="matching-cpp",
        version="",
        uptime_seconds=0,
    )


def default_matching_stats(enabled: bool) -> MatchingStatsView:
    return MatchingStatsView(
        enabled=enabled,
        degraded=False,
        degraded_reason=None,
        live_orders=0,
        trade_count=0,
        tracked_orders=0,
        rejected_orders=0,
        symbols=0,
        best_bid=None,
        best_ask=None,
        submit_order_requests_total=0,
        submit_order_errors_total=0,
        submit_order_rejections_total=0,
        submit_order_latency_p95_ms=0.0,
        submit_order_throughput_rps=0.0,
        trade_throughput_rps=0.0,
        inflight_requests=0,
        inflight_requests_peak=0,
        max_inflight_requests=0,
        backpressure_waits_total=0,
        backpressure_rejections_total=0,
        backpressure_wait_timeouts_total=0,
        backpressure_wait_ms_total=0,
        execution_stream_limit=0,
        submit_latency_window_size=0,
        grpc_min_pollers=0,
        grpc_max_pollers=0,
        grpc_num_cqs=0,
        reason=None,
    )


async def collect_matching_snapshot(
    gateway: MatchingGatewayPort,
    *,
    request_id: str,
) -> MatchingSnapshot:
    health = default_matching_health(enabled=gateway.enabled)
    stats = default_matching_stats(enabled=gateway.enabled)
    if not gateway.enabled:
        return MatchingSnapshot(health=health, stats=stats)

    try:
        health = await gateway.health(request_id=request_id)
    except Exception as exc:  # noqa: BLE001
        health = health.model_copy(
            update={
                "enabled": True,
                "degraded": True,
                "status": "error",
                "reason": str(exc),
                "degraded_reason": str(exc),
                "request_id": request_id,
            }
        )

    try:
        stats = await gateway.get_service_stats(request_id=request_id)
    except Exception as exc:  # noqa: BLE001
        stats = stats.model_copy(
            update={
                "enabled": True,
                "degraded": True,
                "reason": str(exc),
                "degraded_reason": str(exc),
                "request_id": request_id,
            }
        )
    return MatchingSnapshot(health=health, stats=stats)
