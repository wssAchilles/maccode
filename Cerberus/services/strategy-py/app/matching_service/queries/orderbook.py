from __future__ import annotations

import grpc

from app.api.matching_helpers import ensure_matching_enabled
from app.ports import MatchingGatewayPort
from app.schemas import MatchingOrderBookView

from ..fallbacks import build_degraded_orderbook, mark_orderbook_degraded_if_empty
from ..mapping import to_orderbook_view


async def orderbook(
    gateway: MatchingGatewayPort,
    *,
    symbol: str,
    depth: int,
    request_id: str,
) -> MatchingOrderBookView:
    ensure_matching_enabled(gateway)
    normalized_symbol = symbol.strip().upper() or "BTCUSDT"
    bounded_depth = max(1, min(depth, 200))
    try:
        payload = await gateway.get_order_book(
            symbol=normalized_symbol,
            depth=bounded_depth,
            request_id=request_id,
        )
    except grpc.aio.AioRpcError as exc:
        return build_degraded_orderbook(
            symbol=normalized_symbol,
            depth=bounded_depth,
            request_id=request_id,
            reason=f"{exc.code().name}: {exc.details()}",
        )
    except Exception as exc:
        return build_degraded_orderbook(
            symbol=normalized_symbol,
            depth=bounded_depth,
            request_id=request_id,
            reason=f"matching orderbook error: {exc}",
        )
    normalized_payload = mark_orderbook_degraded_if_empty(payload)
    return to_orderbook_view(normalized_payload)
