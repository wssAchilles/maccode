from __future__ import annotations

import grpc

from app.api.matching_helpers import ensure_matching_enabled, raise_gateway_grpc_error
from app.ports import MatchingGatewayPort
from app.schemas import MatchingExecutionView

from ..filters import filter_execution_items
from ..mapping import to_execution_views


async def list_executions(
    gateway: MatchingGatewayPort,
    *,
    account_id: str,
    symbol: str | None,
    order_id: str | None,
    request_id_filter: str | None,
    limit: int,
    request_id: str,
) -> list[MatchingExecutionView]:
    ensure_matching_enabled(gateway)
    try:
        items = await gateway.list_recent_executions(
            account_id=account_id,
            limit=limit,
            request_id=request_id,
        )
    except grpc.aio.AioRpcError as exc:
        raise_gateway_grpc_error("matching stream failed", exc)

    filtered = filter_execution_items(
        items,
        symbol=symbol,
        order_id=order_id,
        request_id_filter=request_id_filter,
    )
    return to_execution_views(filtered, request_id=request_id)
