from __future__ import annotations

from typing import Any

import grpc

from app.order_client_mapping.context import response_context
from app.order_client_proto import order_pb2


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
    schema_version, correlation_id = response_context(response, request_id)
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
    schema_version, correlation_id = response_context(response, request_id)
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


__all__ = [
    "side_to_proto",
    "disabled_submit_result",
    "submit_response_payload",
    "submit_error_payload",
    "cancel_response_payload",
    "cancel_error_payload",
]
