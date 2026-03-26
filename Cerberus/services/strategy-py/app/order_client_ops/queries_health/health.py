from __future__ import annotations

import asyncio
from typing import Any

import grpc

from app.config import settings
from app.order_client_mapping import (
    health_disabled_payload,
    health_error_payload,
    health_ok_payload,
    health_timeout_payload,
)
from app.order_client_ops.metadata import await_unary_with_metadata, degraded_hint
from app.order_client_proto import order_pb2
from app.order_client_rpc import MatchingRpcTransport


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
        response, trailing = await await_unary_with_metadata(call)
        degraded, reason = degraded_hint(trailing)
        if bool(getattr(response, "degraded", False)):
            degraded = True
            if not reason:
                raw_reason = str(getattr(response, "degraded_reason", "")).strip()
                reason = raw_reason or reason
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
