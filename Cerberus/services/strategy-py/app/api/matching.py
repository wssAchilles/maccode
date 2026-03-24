from typing import cast

import grpc
from fastapi import APIRouter, HTTPException, Query, Request

from app.api.matching_helpers import (
    ensure_matching_enabled,
    raise_gateway_grpc_error,
    raise_get_order_error,
    raise_orderbook_error,
)
from app.config import settings
from app.http import request_id_from
from app.redis_worker import RedisMarketWorker
from app.schemas import (
    MatchingCancelRequest,
    MatchingCancelResponse,
    MatchingExecutionView,
    MatchingHealthView,
    MatchingOrderBookView,
    MatchingOrderView,
    MatchingStatsView,
    MatchingSubmitRequest,
    MatchingSubmitResponse,
)
def build_matching_router(worker: RedisMarketWorker) -> APIRouter:
    router = APIRouter()

    @router.post("/api/v1/matching/orders", response_model=MatchingSubmitResponse)
    async def submit_matching_order(
        payload: MatchingSubmitRequest,
        request: Request,
    ) -> MatchingSubmitResponse:
        ensure_matching_enabled(worker)
        rid = request_id_from(request)
        account_id = payload.account_id or settings.strategy_account_id
        result = await worker.matching_client.submit_limit_order(
            account_id=account_id,
            symbol=payload.symbol,
            side=payload.side,
            price=payload.price,
            quantity=payload.quantity,
            client_order_id=payload.client_order_id or "",
            request_id=rid,
        )
        return MatchingSubmitResponse(
            accepted=bool(result.get("accepted", False)),
            order_id=str(result.get("order_id", "")),
            reason=str(result.get("reason", "")),
        )

    @router.post(
        "/api/v1/matching/orders/{order_id}/cancel", response_model=MatchingCancelResponse
    )
    async def cancel_matching_order(
        order_id: str, payload: MatchingCancelRequest, request: Request
    ) -> MatchingCancelResponse:
        ensure_matching_enabled(worker)
        rid = request_id_from(request)
        account_id = payload.account_id or settings.strategy_account_id
        result = await worker.matching_client.cancel_order(
            account_id=account_id,
            order_id=order_id,
            request_id=rid,
        )
        return MatchingCancelResponse(
            canceled=bool(result.get("canceled", False)),
            reason=str(result.get("reason", "")),
        )

    @router.get("/api/v1/matching/orders/{order_id}", response_model=MatchingOrderView)
    async def get_matching_order(
        order_id: str,
        request: Request,
        account_id: str = Query(default=settings.strategy_account_id),
    ) -> MatchingOrderView:
        ensure_matching_enabled(worker)
        try:
            result = await worker.matching_client.get_order(
                account_id=account_id,
                order_id=order_id,
                request_id=request_id_from(request),
            )
        except grpc.aio.AioRpcError as exc:
            raise_get_order_error(exc)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"matching get_order error: {exc}") from exc

        return MatchingOrderView(**result)

    @router.get("/api/v1/matching/executions", response_model=list[MatchingExecutionView])
    async def list_matching_executions(
        request: Request,
        account_id: str = Query(default=settings.strategy_account_id),
        symbol: str | None = Query(default=None),
        limit: int = Query(default=20, ge=1, le=200),
    ) -> list[MatchingExecutionView]:
        ensure_matching_enabled(worker)
        try:
            items = await worker.matching_client.list_recent_executions(
                account_id=account_id,
                limit=limit,
                request_id=request_id_from(request),
            )
            if symbol:
                normalized_symbol = symbol.strip().upper()
                items = [
                    item
                    for item in items
                    if str(item.get("symbol", "")).upper() == normalized_symbol
                ]
            return [MatchingExecutionView(**item) for item in items]
        except grpc.aio.AioRpcError as exc:
            raise_gateway_grpc_error("matching stream failed", exc)

    @router.get("/api/v1/matching/health", response_model=MatchingHealthView)
    async def matching_health(request: Request) -> MatchingHealthView:
        ensure_matching_enabled(worker)
        payload = await worker.matching_client.health(request_id=request_id_from(request))
        reachable = bool(payload.get("reachable", False))
        if not reachable:
            reason = str(payload.get("reason", payload.get("status", "matching unavailable")))
            raise HTTPException(status_code=502, detail=reason)
        return MatchingHealthView(**payload)

    @router.get("/api/v1/matching/stats", response_model=MatchingStatsView)
    async def matching_stats(request: Request) -> MatchingStatsView:
        ensure_matching_enabled(worker)
        try:
            payload = await worker.matching_client.get_service_stats(
                request_id=request_id_from(request)
            )
        except grpc.aio.AioRpcError as exc:
            raise_gateway_grpc_error("matching stats failed", exc)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"matching stats error: {exc}") from exc
        return MatchingStatsView(**payload)

    @router.get("/api/v1/matching/orderbook", response_model=MatchingOrderBookView)
    async def matching_orderbook(
        request: Request,
        symbol: str = Query(default="BTCUSDT", min_length=1, max_length=24),
        depth: int = Query(default=20, ge=1, le=200),
    ) -> MatchingOrderBookView:
        ensure_matching_enabled(worker)
        try:
            payload = await worker.matching_client.get_order_book(
                symbol=symbol,
                depth=depth,
                request_id=request_id_from(request),
            )
        except grpc.aio.AioRpcError as exc:
            raise_orderbook_error(exc)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"matching orderbook error: {exc}") from exc
        return cast(MatchingOrderBookView, MatchingOrderBookView(**payload))

    return router
