from __future__ import annotations

from typing import Any

from app.config import settings
from app.order_client_mapping import execution_payload, order_payload
from app.order_client_proto import order_pb2
from app.order_client_rpc import MatchingRpcTransport


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


__all__ = ["get_order", "list_recent_executions"]
