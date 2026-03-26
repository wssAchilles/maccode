from __future__ import annotations

import grpc
from fastapi import HTTPException

from app.api.matching_helpers import ensure_matching_enabled, raise_get_order_error
from app.redis_worker import RedisMarketWorker
from app.schemas import MatchingOrderView

from ..mapping import to_order_view


async def get_order(
    worker: RedisMarketWorker,
    *,
    order_id: str,
    account_id: str,
    request_id: str,
) -> MatchingOrderView:
    ensure_matching_enabled(worker)
    try:
        result = await worker.matching_client.get_order(
            account_id=account_id,
            order_id=order_id,
            request_id=request_id,
        )
    except grpc.aio.AioRpcError as exc:
        raise_get_order_error(exc)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "matching_get_order_internal_error",
                "message": f"matching get_order error: {exc}",
            },
        ) from exc
    return to_order_view(result, request_id=request_id)
