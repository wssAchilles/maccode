from __future__ import annotations

from app.matching_service.mapping import (
    to_cancel_response,
    to_execution_views,
    to_health_view,
    to_order_view,
    to_orderbook_view,
    to_stats_view,
    to_submit_response,
)
from app.order_client import MatchingOrderClient
from app.schemas import (
    MatchingCancelResponse,
    MatchingExecutionView,
    MatchingHealthView,
    MatchingOrderBookView,
    MatchingOrderView,
    MatchingStatsView,
    MatchingSubmitResponse,
)


class MatchingGatewayAdapter:
    def __init__(self, client: MatchingOrderClient) -> None:
        self._client = client

    @property
    def enabled(self) -> bool:
        return self._client.enabled

    async def submit_limit_order(
        self,
        *,
        account_id: str,
        symbol: str,
        side: str,
        price: float,
        quantity: float,
        client_order_id: str = "",
        request_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> MatchingSubmitResponse:
        payload = await self._client.submit_limit_order(
            account_id=account_id,
            symbol=symbol,
            side=side,
            price=price,
            quantity=quantity,
            client_order_id=client_order_id,
            request_id=request_id,
            idempotency_key=idempotency_key,
        )
        return to_submit_response(payload, request_id=request_id or "")

    async def cancel_order(
        self,
        *,
        account_id: str,
        order_id: str,
        request_id: str | None = None,
    ) -> MatchingCancelResponse:
        payload = await self._client.cancel_order(
            account_id=account_id,
            order_id=order_id,
            request_id=request_id,
        )
        return to_cancel_response(payload, request_id=request_id or "")

    async def get_order(
        self,
        *,
        account_id: str,
        order_id: str,
        request_id: str | None = None,
    ) -> MatchingOrderView:
        payload = await self._client.get_order(
            account_id=account_id,
            order_id=order_id,
            request_id=request_id,
        )
        return to_order_view(payload, request_id=request_id)

    async def list_recent_executions(
        self,
        *,
        account_id: str,
        limit: int = 20,
        request_id: str | None = None,
    ) -> list[MatchingExecutionView]:
        items = await self._client.list_recent_executions(
            account_id=account_id,
            limit=limit,
            request_id=request_id,
        )
        return to_execution_views(items, request_id=request_id)

    async def get_order_book(
        self,
        *,
        symbol: str,
        depth: int = 20,
        request_id: str | None = None,
    ) -> MatchingOrderBookView:
        payload = await self._client.get_order_book(
            symbol=symbol,
            depth=depth,
            request_id=request_id,
        )
        return to_orderbook_view(payload, request_id=request_id)

    async def health(self, request_id: str | None = None) -> MatchingHealthView:
        payload = await self._client.health(request_id=request_id)
        return to_health_view(payload, request_id=request_id)

    async def get_service_stats(
        self,
        request_id: str | None = None,
    ) -> MatchingStatsView:
        payload = await self._client.get_service_stats(request_id=request_id)
        return to_stats_view(payload)
