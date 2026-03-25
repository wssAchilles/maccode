from __future__ import annotations

import logging
from typing import Any

import grpc

from app.config import settings
from app.order_client_mapping import (
    cancel_error_payload,
    cancel_response_payload,
    disabled_submit_result,
    side_to_proto,
    submit_error_payload,
    submit_response_payload,
)
from app.order_client_proto import order_pb2
from app.order_client_rpc import MatchingRpcTransport

logger = logging.getLogger(__name__)


async def submit_limit_order(
    *,
    enabled: bool,
    transport: MatchingRpcTransport,
    account_id: str,
    symbol: str,
    side: str,
    price: float,
    quantity: float,
    client_order_id: str = "",
    request_id: str | None = None,
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    if not enabled:
        return disabled_submit_result("matching disabled", settings.strategy_account_id)
    if side not in ("BUY", "SELL"):
        return disabled_submit_result("side must be BUY or SELL", settings.strategy_account_id)

    stub = await transport.ensure_stub()
    request = order_pb2.SubmitOrderRequest(
        account_id=account_id,
        symbol=symbol,
        side=side_to_proto(side),
        order_type=order_pb2.ORDER_TYPE_LIMIT,
        price=price,
        quantity=quantity,
        client_order_id=client_order_id,
        idempotency_key=(idempotency_key or "").strip(),
        schema_version=settings.event_schema_version,
        correlation_id=(request_id or "").strip(),
    )
    metadata, request_token = transport.build_metadata(request_id)
    if not request.correlation_id:
        request.correlation_id = request_token

    try:
        response = await stub.SubmitOrder(
            request,
            timeout=settings.matching_grpc_timeout_seconds,
            metadata=metadata,
        )
        return submit_response_payload(
            response=response,
            account_id=account_id,
            symbol=symbol,
            price=price,
            quantity=quantity,
            request_id=request_token,
        )
    except grpc.aio.AioRpcError as exc:
        logger.warning(
            "matching SubmitOrder failed code=%s details=%s",
            exc.code().name,
            exc.details(),
        )
        return submit_error_payload(
            exc=exc,
            account_id=account_id,
            symbol=symbol,
            price=price,
            quantity=quantity,
            request_id=request_token,
        )


async def cancel_order(
    *,
    enabled: bool,
    transport: MatchingRpcTransport,
    account_id: str,
    order_id: str,
    request_id: str | None = None,
) -> dict[str, Any]:
    if not enabled:
        return {"canceled": False, "reason": "matching disabled"}

    stub = await transport.ensure_stub()
    metadata, request_token = transport.build_metadata(request_id)
    request = order_pb2.CancelOrderRequest(account_id=account_id, order_id=order_id)
    request.schema_version = settings.event_schema_version
    request.correlation_id = request_token
    try:
        response = await stub.CancelOrder(
            request,
            timeout=settings.matching_grpc_timeout_seconds,
            metadata=metadata,
        )
        return cancel_response_payload(response, request_token)
    except grpc.aio.AioRpcError as exc:
        return cancel_error_payload(exc, request_token)
