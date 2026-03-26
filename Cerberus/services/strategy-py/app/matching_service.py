from __future__ import annotations

from typing import Any, cast

import grpc
from fastapi import HTTPException

from app.api.matching_helpers import (
    ensure_matching_enabled,
    raise_gateway_grpc_error,
    raise_get_order_error,
)
from app.config import settings
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


class MatchingService:
    def __init__(self, *, worker: RedisMarketWorker) -> None:
        self._worker = worker

    async def submit_order(
        self,
        payload: MatchingSubmitRequest,
        *,
        request_id: str,
        idempotency_key: str | None,
    ) -> MatchingSubmitResponse:
        ensure_matching_enabled(self._worker)
        account_id = payload.account_id or settings.strategy_account_id
        result = await self._worker.matching_client.submit_limit_order(
            account_id=account_id,
            symbol=payload.symbol,
            side=payload.side,
            price=payload.price,
            quantity=payload.quantity,
            client_order_id=payload.client_order_id or "",
            request_id=request_id,
            idempotency_key=idempotency_key,
        )
        return MatchingSubmitResponse(
            accepted=bool(result.get("accepted", False)),
            order_id=str(result.get("order_id", "")),
            reason=str(result.get("reason", "")),
            request_id=str(result.get("request_id") or request_id),
            schema_version=result.get("schema_version"),
            correlation_id=result.get("correlation_id"),
        )

    async def cancel_order(
        self,
        *,
        order_id: str,
        payload: MatchingCancelRequest,
        request_id: str,
    ) -> MatchingCancelResponse:
        ensure_matching_enabled(self._worker)
        account_id = payload.account_id or settings.strategy_account_id
        result = await self._worker.matching_client.cancel_order(
            account_id=account_id,
            order_id=order_id,
            request_id=request_id,
        )
        return MatchingCancelResponse(
            canceled=bool(result.get("canceled", False)),
            reason=str(result.get("reason", "")),
            request_id=str(result.get("request_id") or request_id),
            schema_version=result.get("schema_version"),
            correlation_id=result.get("correlation_id"),
        )

    async def get_order(
        self,
        *,
        order_id: str,
        account_id: str,
        request_id: str,
    ) -> MatchingOrderView:
        ensure_matching_enabled(self._worker)
        try:
            result = await self._worker.matching_client.get_order(
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

        return MatchingOrderView(
            **{
                **result,
                "request_id": result.get("request_id") or request_id,
                "schema_version": result.get("schema_version"),
                "correlation_id": result.get("correlation_id"),
            }
        )

    async def list_executions(
        self,
        *,
        account_id: str,
        symbol: str | None,
        order_id: str | None,
        request_id_filter: str | None,
        limit: int,
        request_id: str,
    ) -> list[MatchingExecutionView]:
        ensure_matching_enabled(self._worker)
        try:
            items = await self._worker.matching_client.list_recent_executions(
                account_id=account_id,
                limit=limit,
                request_id=request_id,
            )
        except grpc.aio.AioRpcError as exc:
            raise_gateway_grpc_error("matching stream failed", exc)

        filtered = self._filter_execution_items(
            items,
            symbol=symbol,
            order_id=order_id,
            request_id_filter=request_id_filter,
        )
        return [
            MatchingExecutionView(
                **{
                    **item,
                    "request_id": item.get("request_id") or request_id,
                    "schema_version": item.get("schema_version"),
                    "correlation_id": item.get("correlation_id"),
                }
            )
            for item in filtered
        ]

    async def health(self, *, request_id: str) -> MatchingHealthView:
        ensure_matching_enabled(self._worker)
        payload = await self._worker.matching_client.health(request_id=request_id)
        if not bool(payload.get("reachable", False)):
            reason = str(payload.get("reason") or payload.get("status") or "matching unavailable")
            return MatchingHealthView(
                **{
                    **payload,
                    "degraded": True,
                    "reachable": False,
                    "reason": reason,
                    "request_id": payload.get("request_id") or request_id,
                }
            )
        return MatchingHealthView(**payload)

    async def stats(self, *, request_id: str) -> MatchingStatsView:
        ensure_matching_enabled(self._worker)
        try:
            payload = await self._worker.matching_client.get_service_stats(
                request_id=request_id
            )
        except grpc.aio.AioRpcError as exc:
            return self._degraded_stats(
                request_id=request_id,
                reason=f"{exc.code().name}: {exc.details()}",
            )
        except Exception as exc:
            return self._degraded_stats(
                request_id=request_id,
                reason=f"matching stats error: {exc}",
            )
        return MatchingStatsView(**payload)

    async def orderbook(
        self,
        *,
        symbol: str,
        depth: int,
        request_id: str,
    ) -> MatchingOrderBookView:
        ensure_matching_enabled(self._worker)
        normalized_symbol = symbol.strip().upper() or "BTCUSDT"
        bounded_depth = max(1, min(depth, 200))
        try:
            payload = await self._worker.matching_client.get_order_book(
                symbol=normalized_symbol,
                depth=bounded_depth,
                request_id=request_id,
            )
        except grpc.aio.AioRpcError as exc:
            return self._degraded_orderbook(
                symbol=normalized_symbol,
                depth=bounded_depth,
                request_id=request_id,
                reason=f"{exc.code().name}: {exc.details()}",
            )
        except Exception as exc:
            return self._degraded_orderbook(
                symbol=normalized_symbol,
                depth=bounded_depth,
                request_id=request_id,
                reason=f"matching orderbook error: {exc}",
            )
        if not payload.get("bids") and not payload.get("asks"):
            payload = {
                **payload,
                "degraded": payload.get("degraded", True),
                "reason": payload.get("reason") or "orderbook empty",
            }
        return cast(MatchingOrderBookView, MatchingOrderBookView(**payload))

    def _filter_execution_items(
        self,
        items: list[dict[str, Any]],
        *,
        symbol: str | None,
        order_id: str | None,
        request_id_filter: str | None,
    ) -> list[dict[str, Any]]:
        filtered = items
        normalized_symbol = (symbol or "").strip().upper()
        if normalized_symbol:
            filtered = [
                item
                for item in filtered
                if str(item.get("symbol", "")).upper() == normalized_symbol
            ]

        normalized_order_id = (order_id or "").strip()
        if normalized_order_id:
            filtered = [
                item for item in filtered if str(item.get("order_id", "")) == normalized_order_id
            ]

        normalized_request_id = (request_id_filter or "").strip()
        if normalized_request_id:
            filtered = [
                item
                for item in filtered
                if str(item.get("request_id", "")) == normalized_request_id
            ]
        return filtered

    def _degraded_stats(self, *, request_id: str, reason: str) -> MatchingStatsView:
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
            request_id=request_id,
            reason=reason,
        )

    def _degraded_orderbook(
        self,
        *,
        symbol: str,
        depth: int,
        request_id: str,
        reason: str,
    ) -> MatchingOrderBookView:
        return MatchingOrderBookView(
            enabled=True,
            degraded=True,
            symbol=symbol,
            depth=depth,
            bids=[],
            asks=[],
            generated_at_ms=0,
            request_id=request_id,
            reason=reason,
        )
