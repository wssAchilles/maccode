from __future__ import annotations

from typing import Any

import grpc

from app.order_client_mapping.context import normalize_text, response_context


def health_disabled_payload() -> dict[str, Any]:
    return {
        "enabled": False,
        "reachable": False,
        "degraded": False,
        "degraded_reason": None,
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
    schema_version, correlation_id = response_context(response, request_id)
    response_degraded = bool(getattr(response, "degraded", False))
    response_degraded_reason = normalize_text(getattr(response, "degraded_reason", None))
    effective_degraded = degraded or response_degraded
    effective_reason = degraded_reason or response_degraded_reason
    return {
        "enabled": True,
        "reachable": True,
        "degraded": effective_degraded,
        "degraded_reason": effective_reason,
        "status": response.status,
        "service": response.service,
        "version": response.version,
        "uptime_seconds": int(response.uptime_seconds),
        "request_id": request_id,
        "reason": effective_reason,
        "schema_version": schema_version,
        "correlation_id": correlation_id,
    }


def health_timeout_payload(request_id: str) -> dict[str, Any]:
    return {
        "enabled": True,
        "reachable": False,
        "degraded": True,
        "degraded_reason": "matching health timeout",
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
    reason = exc.details()
    return {
        "enabled": True,
        "reachable": False,
        "degraded": True,
        "degraded_reason": reason,
        "status": exc.code().name,
        "service": "matching-cpp",
        "version": "",
        "uptime_seconds": 0,
        "reason": reason,
        "request_id": request_id,
        "schema_version": None,
        "correlation_id": request_id,
    }


__all__ = [
    "health_disabled_payload",
    "health_ok_payload",
    "health_timeout_payload",
    "health_error_payload",
]
