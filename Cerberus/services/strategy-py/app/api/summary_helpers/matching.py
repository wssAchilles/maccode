from __future__ import annotations

import grpc

from app.config import settings
from app.redis_worker import RedisMarketWorker

from .components import component_ok


def orderbook_degraded_payload(
    *,
    symbol: str,
    depth: int,
    request_id: str,
    reason: str,
) -> dict[str, object]:
    return {
        "enabled": settings.matching_enabled,
        "degraded": True,
        "symbol": symbol,
        "depth": depth,
        "bids": [],
        "asks": [],
        "generated_at_ms": 0,
        "request_id": request_id,
        "reason": reason,
        "schema_version": settings.event_schema_version,
        "correlation_id": request_id,
    }


async def build_matching_orderbook_component(
    worker: RedisMarketWorker,
    *,
    symbol: str,
    depth: int,
    request_id: str,
) -> dict[str, object]:
    try:
        payload = await worker.matching_client.get_order_book(
            symbol=symbol,
            depth=depth,
            request_id=request_id,
        )
    except grpc.aio.AioRpcError as exc:
        return component_ok(
            orderbook_degraded_payload(
                symbol=symbol,
                depth=depth,
                request_id=request_id,
                reason=f"{exc.code().name}: {exc.details()}",
            )
        )
    except Exception as exc:
        return component_ok(
            orderbook_degraded_payload(
                symbol=symbol,
                depth=depth,
                request_id=request_id,
                reason=f"matching orderbook error: {exc}",
            )
        )

    if not payload.get("bids") and not payload.get("asks"):
        payload = {
            **payload,
            "degraded": payload.get("degraded", True),
            "reason": payload.get("reason") or "orderbook empty",
        }
    return component_ok(payload)


__all__ = ["build_matching_orderbook_component", "orderbook_degraded_payload"]
