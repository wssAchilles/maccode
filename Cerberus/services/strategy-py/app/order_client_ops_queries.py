from __future__ import annotations

import asyncio
from typing import Any

import grpc

from app.config import settings
from app.order_client_mapping import (
    execution_payload,
    health_disabled_payload,
    health_error_payload,
    health_ok_payload,
    health_timeout_payload,
    order_book_disabled_payload,
    order_book_payload,
    order_payload,
    stats_disabled_payload,
    stats_payload,
)
from app.order_client_proto import order_pb2
from app.order_client_rpc import MatchingRpcTransport


def _metadata_to_dict(metadata: grpc.aio.Metadata | None) -> dict[str, str]:
    if metadata is None:
        return {}
    normalized: dict[str, str] = {}
    for key, value in metadata:
        key_text = str(key).strip().lower()
        if not key_text:
            continue
        if isinstance(value, bytes):
            value_text = value.decode("utf-8", errors="ignore").strip()
        else:
            value_text = str(value).strip()
        if value_text:
            normalized[key_text] = value_text
    return normalized


def _degraded_hint(metadata: dict[str, str]) -> tuple[bool, str | None]:
    raw = metadata.get("x-cerberus-degraded", "")
    degraded = raw.lower() in {"1", "true", "yes", "on"}
    reason = metadata.get("x-cerberus-degraded-reason")
    return degraded, reason


async def _await_unary_with_metadata(call: Any) -> tuple[Any, dict[str, str]]:
    response = await call
    trailing = await call.trailing_metadata()
    return response, _metadata_to_dict(trailing)


async def get_order(
    *,
    enabled: bool,
    transport: MatchingRpcTransport,
    account_id: str,
    order_id: str,
    request_id: str | None = None,
) -> dict[str, Any]:
    if not enabled:
        raise RuntimeError("matching disabled")

    stub = await transport.ensure_stub()
    metadata, request_token = transport.build_metadata(request_id)
    request = order_pb2.GetOrderRequest(
        account_id=account_id,
        order_id=order_id,
        schema_version=settings.event_schema_version,
        correlation_id=request_token,
    )
    response = await stub.GetOrder(
        request,
        timeout=settings.matching_grpc_timeout_seconds,
        metadata=metadata,
    )
    return order_payload(response, request_token)


async def list_recent_executions(
    *,
    enabled: bool,
    transport: MatchingRpcTransport,
    account_id: str,
    limit: int = 20,
    request_id: str | None = None,
) -> list[dict[str, Any]]:
    if not enabled:
        return []

    stub = await transport.ensure_stub()
    metadata, request_token = transport.build_metadata(request_id)
    call = stub.StreamExecutions(
        order_pb2.StreamExecutionsRequest(
            account_id=account_id,
            schema_version=settings.event_schema_version,
            correlation_id=request_token,
        ),
        timeout=settings.matching_grpc_timeout_seconds,
        metadata=metadata,
    )

    executions: list[dict[str, Any]] = []
    async for item in call:
        executions.append(execution_payload(item, account_id, request_token))
        if len(executions) >= limit:
            break
    return executions


async def get_order_book(
    *,
    enabled: bool,
    transport: MatchingRpcTransport,
    symbol: str,
    depth: int = 20,
    request_id: str | None = None,
) -> dict[str, Any]:
    if not enabled:
        return order_book_disabled_payload(symbol, depth)

    clean_symbol = symbol.strip().upper()
    bounded_depth = max(1, min(depth, 200))
    stub = await transport.ensure_stub()
    metadata, request_token = transport.build_metadata(request_id)
    call = stub.GetOrderBook(
        order_pb2.GetOrderBookRequest(
            symbol=clean_symbol,
            depth=bounded_depth,
            schema_version=settings.event_schema_version,
            correlation_id=request_token,
        ),
        timeout=settings.matching_grpc_timeout_seconds,
        metadata=metadata,
    )
    response, trailing = await _await_unary_with_metadata(call)
    degraded, reason = _degraded_hint(trailing)
    return order_book_payload(
        response=response,
        fallback_symbol=clean_symbol,
        depth=bounded_depth,
        request_id=request_token,
        degraded=degraded,
        degraded_reason=reason,
    )


async def health(
    *,
    enabled: bool,
    transport: MatchingRpcTransport,
    request_id: str | None = None,
) -> dict[str, Any]:
    if not enabled:
        return health_disabled_payload()

    stub = await transport.ensure_stub()
    metadata, request_token = transport.build_metadata(request_id)
    try:
        await transport.wait_ready(settings.matching_grpc_timeout_seconds)
        call = stub.Health(
            order_pb2.HealthRequest(),
            timeout=settings.matching_grpc_timeout_seconds,
            metadata=metadata,
        )
        response, trailing = await _await_unary_with_metadata(call)
        degraded, reason = _degraded_hint(trailing)
        response_status = str(getattr(response, "status", "")).strip()
        if response_status.lower().startswith("degraded"):
            degraded = True
            if not reason:
                reason = response_status
        return health_ok_payload(
            response,
            request_token,
            degraded=degraded,
            degraded_reason=reason,
        )
    except asyncio.TimeoutError:
        return health_timeout_payload(request_token)
    except grpc.aio.AioRpcError as exc:
        return health_error_payload(exc, request_token)


async def get_service_stats(
    *,
    enabled: bool,
    transport: MatchingRpcTransport,
    request_id: str | None = None,
) -> dict[str, Any]:
    if not enabled:
        return stats_disabled_payload()

    stub = await transport.ensure_stub()
    metadata, request_token = transport.build_metadata(request_id)
    call = stub.GetServiceStats(
        order_pb2.GetServiceStatsRequest(),
        timeout=settings.matching_grpc_timeout_seconds,
        metadata=metadata,
    )
    response, trailing = await _await_unary_with_metadata(call)
    degraded, reason = _degraded_hint(trailing)
    return stats_payload(response, request_token, degraded=degraded, degraded_reason=reason)
