from __future__ import annotations

from typing import Any

import grpc


def _normalize_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def _response_context(response: Any, fallback_request_id: str) -> tuple[str | None, str]:
    schema_version = _normalize_text(getattr(response, "schema_version", None))
    correlation_id = (
        _normalize_text(getattr(response, "correlation_id", None)) or fallback_request_id
    )
    return schema_version, correlation_id


def health_disabled_payload() -> dict[str, Any]:
    return {
        "enabled": False,
        "reachable": False,
        "degraded": False,
        "status": "disabled",
        "service": "matching-cpp",
        "version": "",
        "uptime_seconds": 0,
        "schema_version": None,
        "correlation_id": None,
    }


def health_ok_payload(
    response: Any,
    request_id: str,
    *,
    degraded: bool = False,
    degraded_reason: str | None = None,
) -> dict[str, Any]:
    schema_version, correlation_id = _response_context(response, request_id)
    return {
        "enabled": True,
        "reachable": True,
        "degraded": degraded,
        "status": response.status,
        "service": response.service,
        "version": response.version,
        "uptime_seconds": int(response.uptime_seconds),
        "request_id": request_id,
        "reason": degraded_reason,
        "schema_version": schema_version,
        "correlation_id": correlation_id,
    }


def health_timeout_payload(request_id: str) -> dict[str, Any]:
    return {
        "enabled": True,
        "reachable": False,
        "degraded": True,
        "status": "timeout",
        "service": "matching-cpp",
        "version": "",
        "uptime_seconds": 0,
        "request_id": request_id,
        "reason": "matching health timeout",
        "schema_version": None,
        "correlation_id": request_id,
    }


def health_error_payload(exc: grpc.aio.AioRpcError, request_id: str) -> dict[str, Any]:
    return {
        "enabled": True,
        "reachable": False,
        "degraded": True,
        "status": exc.code().name,
        "service": "matching-cpp",
        "version": "",
        "uptime_seconds": 0,
        "reason": exc.details(),
        "request_id": request_id,
        "schema_version": None,
        "correlation_id": request_id,
    }


def stats_disabled_payload() -> dict[str, Any]:
    return {
        "enabled": False,
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
    schema_version, correlation_id = _response_context(response, request_id)
    return {
        "enabled": True,
        "degraded": degraded,
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
        "request_id": request_id,
        "reason": degraded_reason,
        "schema_version": schema_version,
        "correlation_id": correlation_id,
    }
