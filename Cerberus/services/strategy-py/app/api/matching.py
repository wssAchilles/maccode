from fastapi import APIRouter, Query, Request

from app.config import settings
from app.http import idempotency_key_from, request_id_from
from app.matching_service import MatchingService
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


def build_matching_router(service: MatchingService) -> APIRouter:
    router = APIRouter()

    @router.post("/api/v1/matching/orders", response_model=MatchingSubmitResponse)
    async def submit_matching_order(
        payload: MatchingSubmitRequest,
        request: Request,
    ) -> MatchingSubmitResponse:
        return await service.submit_order(
            payload,
            request_id=request_id_from(request),
            idempotency_key=idempotency_key_from(request),
        )

    @router.post(
        "/api/v1/matching/orders/{order_id}/cancel", response_model=MatchingCancelResponse
    )
    async def cancel_matching_order(
        order_id: str, payload: MatchingCancelRequest, request: Request
    ) -> MatchingCancelResponse:
        return await service.cancel_order(
            order_id=order_id,
            payload=payload,
            request_id=request_id_from(request),
        )

    @router.get("/api/v1/matching/orders/{order_id}", response_model=MatchingOrderView)
    async def get_matching_order(
        order_id: str,
        request: Request,
        account_id: str = Query(default=settings.strategy_account_id),
    ) -> MatchingOrderView:
        return await service.get_order(
            order_id=order_id,
            account_id=account_id,
            request_id=request_id_from(request),
        )

    @router.get("/api/v1/matching/executions", response_model=list[MatchingExecutionView])
    async def list_matching_executions(
        request: Request,
        account_id: str = Query(default=settings.strategy_account_id),
        symbol: str | None = Query(default=None),
        order_id: str | None = Query(default=None),
        request_id: str | None = Query(default=None),
        limit: int = Query(default=20, ge=1, le=200),
    ) -> list[MatchingExecutionView]:
        return await service.list_executions(
            account_id=account_id,
            symbol=symbol,
            order_id=order_id,
            request_id_filter=request_id,
            limit=limit,
            request_id=request_id_from(request),
        )

    @router.get("/api/v1/matching/health", response_model=MatchingHealthView)
    async def matching_health(request: Request) -> MatchingHealthView:
        return await service.health(request_id=request_id_from(request))

    @router.get("/api/v1/matching/stats", response_model=MatchingStatsView)
    async def matching_stats(request: Request) -> MatchingStatsView:
        return await service.stats(request_id=request_id_from(request))

    @router.get("/api/v1/matching/orderbook", response_model=MatchingOrderBookView)
    async def matching_orderbook(
        request: Request,
        symbol: str = Query(default="BTCUSDT", min_length=1, max_length=24),
        depth: int = Query(default=20, ge=1, le=200),
    ) -> MatchingOrderBookView:
        return await service.orderbook(
            symbol=symbol,
            depth=depth,
            request_id=request_id_from(request),
        )

    return router
