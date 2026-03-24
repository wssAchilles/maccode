from __future__ import annotations

from typing import Any

import grpc


def health_disabled_payload() -> dict[str, Any]:
    return {
        "enabled": False,
        "reachable": False,
        "status": "disabled",
        "service": "matching-cpp",
        "version": "",
        "uptime_seconds": 0,
    }


def health_ok_payload(response: Any, request_id: str) -> dict[str, Any]:
    return {
        "enabled": True,
        "reachable": True,
        "status": response.status,
        "service": response.service,
        "version": response.version,
        "uptime_seconds": int(response.uptime_seconds),
        "request_id": request_id,
    }


def health_timeout_payload(request_id: str) -> dict[str, Any]:
    return {
        "enabled": True,
        "reachable": False,
        "status": "timeout",
        "service": "matching-cpp",
        "version": "",
        "uptime_seconds": 0,
        "request_id": request_id,
    }


def health_error_payload(exc: grpc.aio.AioRpcError, request_id: str) -> dict[str, Any]:
    return {
        "enabled": True,
        "reachable": False,
        "status": exc.code().name,
        "service": "matching-cpp",
        "version": "",
        "uptime_seconds": 0,
        "reason": exc.details(),
        "request_id": request_id,
    }


def stats_disabled_payload() -> dict[str, Any]:
    return {
        "enabled": False,
        "live_orders": 0,
        "trade_count": 0,
        "tracked_orders": 0,
        "rejected_orders": 0,
        "symbols": 0,
        "best_bid": None,
        "best_ask": None,
    }


def stats_payload(response: Any, request_id: str) -> dict[str, Any]:
    return {
        "enabled": True,
        "live_orders": int(response.live_orders),
        "trade_count": int(response.trade_count),
        "tracked_orders": int(response.tracked_orders),
        "rejected_orders": int(response.rejected_orders),
        "symbols": int(response.symbols),
        "best_bid": float(response.best_bid) if response.has_best_bid else None,
        "best_ask": float(response.best_ask) if response.has_best_ask else None,
        "request_id": request_id,
    }
