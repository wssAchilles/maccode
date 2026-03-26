from __future__ import annotations

from typing import Any

from app.config import settings
from app.order_client_mapping import stats_disabled_payload, stats_payload
from app.order_client_ops.metadata import await_unary_with_metadata, degraded_hint
from app.order_client_proto import order_pb2
from app.order_client_rpc import MatchingRpcTransport


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
    response, trailing = await await_unary_with_metadata(call)
    degraded, reason = degraded_hint(trailing)
    return stats_payload(response, request_token, degraded=degraded, degraded_reason=reason)
