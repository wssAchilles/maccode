from __future__ import annotations

from typing import Any

from app.config import settings
from app.order_client_mapping import order_book_disabled_payload, order_book_payload
from app.order_client_ops.metadata import await_unary_with_metadata, degraded_hint
from app.order_client_proto import order_pb2
from app.order_client_rpc import MatchingRpcTransport


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
    response, trailing = await await_unary_with_metadata(call)
    degraded, reason = degraded_hint(trailing)
    return order_book_payload(
        response=response,
        fallback_symbol=clean_symbol,
        depth=bounded_depth,
        request_id=request_token,
        degraded=degraded,
        degraded_reason=reason,
    )
