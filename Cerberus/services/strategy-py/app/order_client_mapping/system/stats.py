from __future__ import annotations

from typing import Any

from app.order_client_mapping.context import normalize_text, response_context


def stats_disabled_payload() -> dict[str, Any]:
    return {
        "enabled": False,
        "degraded": False,
        "degraded_reason": None,
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
        "inflight_requests": 0,
        "inflight_requests_peak": 0,
        "max_inflight_requests": 0,
        "backpressure_waits_total": 0,
        "backpressure_rejections_total": 0,
        "backpressure_wait_timeouts_total": 0,
        "backpressure_wait_ms_total": 0,
        "execution_stream_limit": 0,
        "submit_latency_window_size": 0,
        "grpc_min_pollers": 0,
        "grpc_max_pollers": 0,
        "grpc_num_cqs": 0,
        "schema_version": None,
        "correlation_id": None,
    }


def stats_payload(
    response: Any,
    request_id: str,
    *,
    degraded: bool = False,
    degraded_reason: str | None = None,
) -> dict[str, Any]:
    schema_version, correlation_id = response_context(response, request_id)
    response_degraded = bool(getattr(response, "degraded", False))
    response_degraded_reason = normalize_text(getattr(response, "degraded_reason", None))
    effective_degraded = degraded or response_degraded
    effective_reason = degraded_reason or response_degraded_reason
    return {
        "enabled": True,
        "degraded": effective_degraded,
        "degraded_reason": effective_reason,
        "live_orders": int(response.live_orders),
        "trade_count": int(response.trade_count),
        "tracked_orders": int(response.tracked_orders),
        "rejected_orders": int(response.rejected_orders),
        "symbols": int(response.symbols),
        "best_bid": float(response.best_bid) if response.has_best_bid else None,
        "best_ask": float(response.best_ask) if response.has_best_ask else None,
        "submit_order_requests_total": int(
            getattr(response, "submit_order_requests_total", 0)
        ),
        "submit_order_errors_total": int(getattr(response, "submit_order_errors_total", 0)),
        "submit_order_rejections_total": int(
            getattr(response, "submit_order_rejections_total", 0)
        ),
        "submit_order_latency_p95_ms": float(
            getattr(response, "submit_order_latency_p95_ms", 0.0)
        ),
        "submit_order_throughput_rps": float(
            getattr(response, "submit_order_throughput_rps", 0.0)
        ),
        "trade_throughput_rps": float(getattr(response, "trade_throughput_rps", 0.0)),
        "inflight_requests": int(getattr(response, "inflight_requests", 0)),
        "inflight_requests_peak": int(getattr(response, "inflight_requests_peak", 0)),
        "max_inflight_requests": int(getattr(response, "max_inflight_requests", 0)),
        "backpressure_waits_total": int(getattr(response, "backpressure_waits_total", 0)),
        "backpressure_rejections_total": int(
            getattr(response, "backpressure_rejections_total", 0)
        ),
        "backpressure_wait_timeouts_total": int(
            getattr(response, "backpressure_wait_timeouts_total", 0)
        ),
        "backpressure_wait_ms_total": int(getattr(response, "backpressure_wait_ms_total", 0)),
        "execution_stream_limit": int(getattr(response, "execution_stream_limit", 0)),
        "submit_latency_window_size": int(
            getattr(response, "submit_latency_window_size", 0)
        ),
        "grpc_min_pollers": int(getattr(response, "grpc_min_pollers", 0)),
        "grpc_max_pollers": int(getattr(response, "grpc_max_pollers", 0)),
        "grpc_num_cqs": int(getattr(response, "grpc_num_cqs", 0)),
        "request_id": request_id,
        "reason": effective_reason,
        "schema_version": schema_version,
        "correlation_id": correlation_id,
    }


__all__ = ["stats_disabled_payload", "stats_payload"]
