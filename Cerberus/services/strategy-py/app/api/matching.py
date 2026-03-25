from typing import cast

import grpc
from fastapi import APIRouter, HTTPException, Query, Request

from app.api.matching_helpers import (
    ensure_matching_enabled,
    raise_gateway_grpc_error,
    raise_get_order_error,
)
from app.config import settings
from app.http import idempotency_key_from, request_id_from
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
            idempotency_key=idempotency_key_from(request),
        )
        return MatchingSubmitResponse(
            accepted=bool(result.get("accepted", False)),
            order_id=str(result.get("order_id", "")),
            reason=str(result.get("reason", "")),
            request_id=str(result.get("request_id") or rid),
            schema_version=result.get("schema_version"),
            correlation_id=result.get("correlation_id"),
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
            request_id=str(result.get("request_id") or rid),
            schema_version=result.get("schema_version"),
            correlation_id=result.get("correlation_id"),
        )

    @router.get("/api/v1/matching/orders/{order_id}", response_model=MatchingOrderView)
    async def get_matching_order(
        order_id: str,
        request: Request,
        account_id: str = Query(default=settings.strategy_account_id),
    ) -> MatchingOrderView:
        ensure_matching_enabled(worker)
        rid = request_id_from(request)
        try:
            result = await worker.matching_client.get_order(
                account_id=account_id,
                order_id=order_id,
                request_id=rid,
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

        return MatchingOrderView(
            **{
                **result,
                "request_id": result.get("request_id") or rid,
                "schema_version": result.get("schema_version"),
                "correlation_id": result.get("correlation_id"),
            }
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
        ensure_matching_enabled(worker)
        rid = request_id_from(request)
        try:
            items = await worker.matching_client.list_recent_executions(
                account_id=account_id,
                limit=limit,
                request_id=rid,
            )
            if symbol:
                normalized_symbol = symbol.strip().upper()
                items = [
                    item
                    for item in items
                    if str(item.get("symbol", "")).upper() == normalized_symbol
                ]
            if order_id:
                normalized_order_id = order_id.strip()
                if normalized_order_id:
                    items = [
                        item
                        for item in items
                        if str(item.get("order_id", "")) == normalized_order_id
                    ]
            if request_id:
                normalized_request_id = request_id.strip()
                if normalized_request_id:
                    items = [
                        item
                        for item in items
                        if str(item.get("request_id", "")) == normalized_request_id
                    ]
            return [
                MatchingExecutionView(
                    **{
                        **item,
                        "request_id": item.get("request_id") or rid,
                        "schema_version": item.get("schema_version"),
                        "correlation_id": item.get("correlation_id"),
                    }
                )
                for item in items
            ]
        except grpc.aio.AioRpcError as exc:
            raise_gateway_grpc_error("matching stream failed", exc)

    @router.get("/api/v1/matching/health", response_model=MatchingHealthView)
    async def matching_health(request: Request) -> MatchingHealthView:
        ensure_matching_enabled(worker)
        rid = request_id_from(request)
        payload = await worker.matching_client.health(request_id=request_id_from(request))
        reachable = bool(payload.get("reachable", False))
        if not reachable:
            reason = str(payload.get("reason") or payload.get("status") or "matching unavailable")
            return MatchingHealthView(
                **{
                    **payload,
                    "degraded": True,
                    "reachable": False,
                    "reason": reason,
                    "request_id": payload.get("request_id") or rid,
                }
            )
        return MatchingHealthView(**payload)

    @router.get("/api/v1/matching/stats", response_model=MatchingStatsView)
    async def matching_stats(request: Request) -> MatchingStatsView:
        ensure_matching_enabled(worker)
        rid = request_id_from(request)
        try:
            payload = await worker.matching_client.get_service_stats(
                request_id=rid
            )
        except grpc.aio.AioRpcError as exc:
            return MatchingStatsView(
                enabled=True,
                degraded=True,
                live_orders=0,
                trade_count=0,
                tracked_orders=0,
                rejected_orders=0,
                symbols=0,
                best_bid=None,
                best_ask=None,
                request_id=rid,
                reason=f"{exc.code().name}: {exc.details()}",
            )
        except Exception as exc:
            return MatchingStatsView(
                enabled=True,
                degraded=True,
                live_orders=0,
                trade_count=0,
                tracked_orders=0,
                rejected_orders=0,
                symbols=0,
                best_bid=None,
                best_ask=None,
                request_id=rid,
                reason=f"matching stats error: {exc}",
            )
        return MatchingStatsView(**payload)

    @router.get("/api/v1/matching/orderbook", response_model=MatchingOrderBookView)
    async def matching_orderbook(
        request: Request,
        symbol: str = Query(default="BTCUSDT", min_length=1, max_length=24),
        depth: int = Query(default=20, ge=1, le=200),
    ) -> MatchingOrderBookView:
        ensure_matching_enabled(worker)
        rid = request_id_from(request)
        normalized_symbol = symbol.strip().upper()
        bounded_depth = max(1, min(depth, 200))
        try:
            payload = await worker.matching_client.get_order_book(
                symbol=normalized_symbol,
                depth=bounded_depth,
                request_id=rid,
            )
        except grpc.aio.AioRpcError as exc:
            return MatchingOrderBookView(
                enabled=True,
                degraded=True,
                symbol=normalized_symbol,
                depth=bounded_depth,
                bids=[],
                asks=[],
                generated_at_ms=0,
                request_id=rid,
                reason=f"{exc.code().name}: {exc.details()}",
            )
        except Exception as exc:
            return MatchingOrderBookView(
                enabled=True,
                degraded=True,
                symbol=normalized_symbol,
                depth=bounded_depth,
                bids=[],
                asks=[],
                generated_at_ms=0,
                request_id=rid,
                reason=f"matching orderbook error: {exc}",
            )
        if not payload.get("bids") and not payload.get("asks"):
            payload = {
                **payload,
                "degraded": payload.get("degraded", True),
                "reason": payload.get("reason") or "orderbook empty",
            }
        return cast(MatchingOrderBookView, MatchingOrderBookView(**payload))

    return router
