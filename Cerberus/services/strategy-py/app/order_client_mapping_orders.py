from __future__ import annotations

from datetime import timezone
from typing import Any

import grpc

from app.order_client_proto import order_pb2


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


def side_to_proto(side: str) -> int:
    return order_pb2.SIDE_BUY if side == "BUY" else order_pb2.SIDE_SELL


def disabled_submit_result(reason: str, account_id: str) -> dict[str, Any]:
    return {
        "accepted": False,
        "order_id": "",
        "reason": reason,
        "account_id": account_id,
        "symbol": "",
        "price": 0.0,
        "quantity": 0.0,
        "schema_version": None,
        "correlation_id": None,
    }


def submit_response_payload(
    *,
    response: Any,
    account_id: str,
    symbol: str,
    price: float,
    quantity: float,
    request_id: str,
) -> dict[str, Any]:
    schema_version, correlation_id = _response_context(response, request_id)
    return {
        "accepted": bool(response.accepted),
        "order_id": response.order_id,
        "reason": response.reason,
        "account_id": account_id,
        "symbol": symbol,
        "price": price,
        "quantity": quantity,
        "request_id": request_id,
        "schema_version": schema_version,
        "correlation_id": correlation_id,
    }


def submit_error_payload(
    *,
    exc: grpc.aio.AioRpcError,
    account_id: str,
    symbol: str,
    price: float,
    quantity: float,
    request_id: str,
) -> dict[str, Any]:
    return {
        "accepted": False,
        "order_id": "",
        "reason": f"{exc.code().name}: {exc.details()}",
        "account_id": account_id,
        "symbol": symbol,
        "price": price,
        "quantity": quantity,
        "request_id": request_id,
        "schema_version": None,
        "correlation_id": request_id,
    }


def cancel_response_payload(response: Any, request_id: str) -> dict[str, Any]:
    schema_version, correlation_id = _response_context(response, request_id)
    return {
        "canceled": bool(response.canceled),
        "reason": response.reason,
        "request_id": request_id,
        "schema_version": schema_version,
        "correlation_id": correlation_id,
    }


def cancel_error_payload(exc: grpc.aio.AioRpcError, request_id: str) -> dict[str, Any]:
    return {
        "canceled": False,
        "reason": f"{exc.code().name}: {exc.details()}",
        "request_id": request_id,
        "schema_version": None,
        "correlation_id": request_id,
    }


def order_payload(response: Any, request_id: str) -> dict[str, Any]:
    schema_version, correlation_id = _response_context(response, request_id)
    return {
        "order_id": response.order_id,
        "account_id": response.account_id,
        "symbol": response.symbol,
        "side": order_pb2.Side.Name(response.side),
        "order_type": order_pb2.OrderType.Name(response.order_type),
        "price": response.price,
        "quantity": response.quantity,
        "filled_quantity": response.filled_quantity,
        "status": order_pb2.OrderStatus.Name(response.status),
        "updated_at": response.updated_at.ToDatetime(tzinfo=timezone.utc).isoformat()
        if response.HasField("updated_at")
        else None,
        "request_id": request_id,
        "schema_version": schema_version,
        "correlation_id": correlation_id,
    }


def execution_payload(item: Any, account_id: str, request_id: str) -> dict[str, Any]:
    schema_version, correlation_id = _response_context(item, request_id)
    return {
        "execution_id": item.execution_id,
        "order_id": item.order_id,
        "account_id": account_id,
        "symbol": item.symbol,
        "price": item.price,
        "quantity": item.quantity,
        "event_time": item.event_time.ToDatetime(tzinfo=timezone.utc).isoformat()
        if item.HasField("event_time")
        else None,
        "request_id": request_id,
        "schema_version": schema_version,
        "correlation_id": correlation_id,
    }


def order_book_disabled_payload(symbol: str, depth: int) -> dict[str, Any]:
    return {
        "enabled": False,
        "degraded": False,
        "symbol": symbol,
        "depth": depth,
        "bids": [],
        "asks": [],
        "generated_at_ms": 0,
        "reason": "matching disabled",
        "schema_version": None,
        "correlation_id": None,
    }


def order_book_payload(
    *,
    response: Any,
    fallback_symbol: str,
    depth: int,
    request_id: str,
    degraded: bool = False,
    degraded_reason: str | None = None,
) -> dict[str, Any]:
    schema_version, correlation_id = _response_context(response, request_id)
    return {
        "enabled": True,
        "degraded": degraded,
        "symbol": response.symbol or fallback_symbol,
        "depth": depth,
        "bids": _book_levels(response.bids),
        "asks": _book_levels(response.asks),
        "generated_at_ms": int(response.generated_at_ms),
        "request_id": request_id,
        "reason": degraded_reason,
        "schema_version": schema_version,
        "correlation_id": correlation_id,
    }


def _book_levels(levels: Any) -> list[dict[str, float | int]]:
    return [
        {
            "price": float(level.price),
            "total_quantity": float(level.total_quantity),
            "order_count": int(level.order_count),
        }
        for level in levels
    ]
