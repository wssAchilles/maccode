from __future__ import annotations

from app.ports import MatchingGatewayPort
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

from .commands import cancel_order, submit_order
from .queries import get_order, list_executions, orderbook
from .status import health, stats


class MatchingService:
    def __init__(self, *, gateway: MatchingGatewayPort) -> None:
        self._gateway = gateway

    async def submit_order(
        self,
        payload: MatchingSubmitRequest,
        *,
        request_id: str,
        idempotency_key: str | None,
    ) -> MatchingSubmitResponse:
        return await submit_order(
            self._gateway,
            payload,
            request_id=request_id,
            idempotency_key=idempotency_key,
        )

    async def cancel_order(
        self,
        *,
        order_id: str,
        payload: MatchingCancelRequest,
        request_id: str,
    ) -> MatchingCancelResponse:
        return await cancel_order(
            self._gateway,
            order_id=order_id,
            payload=payload,
            request_id=request_id,
        )

    async def get_order(
        self,
        *,
        order_id: str,
        account_id: str,
        request_id: str,
    ) -> MatchingOrderView:
        return await get_order(
            self._gateway,
            order_id=order_id,
            account_id=account_id,
            request_id=request_id,
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
        return await list_executions(
            self._gateway,
            account_id=account_id,
            symbol=symbol,
            order_id=order_id,
            request_id_filter=request_id_filter,
            limit=limit,
            request_id=request_id,
        )

    async def health(self, *, request_id: str) -> MatchingHealthView:
        return await health(self._gateway, request_id=request_id)

    async def stats(self, *, request_id: str) -> MatchingStatsView:
        return await stats(self._gateway, request_id=request_id)

    async def orderbook(
        self,
        *,
        symbol: str,
        depth: int,
        request_id: str,
    ) -> MatchingOrderBookView:
        return await orderbook(
            self._gateway,
            symbol=symbol,
            depth=depth,
            request_id=request_id,
        )
