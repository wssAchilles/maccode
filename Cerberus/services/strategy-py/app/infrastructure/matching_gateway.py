from __future__ import annotations

from typing import Any

from app.order_client import MatchingOrderClient


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
    ) -> dict[str, Any]:
        return await self._client.submit_limit_order(
            account_id=account_id,
            symbol=symbol,
            side=side,
            price=price,
            quantity=quantity,
            client_order_id=client_order_id,
            request_id=request_id,
            idempotency_key=idempotency_key,
        )

    async def cancel_order(
        self,
        *,
        account_id: str,
        order_id: str,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        return await self._client.cancel_order(
            account_id=account_id,
            order_id=order_id,
            request_id=request_id,
        )

    async def get_order(
        self,
        *,
        account_id: str,
        order_id: str,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        return await self._client.get_order(
            account_id=account_id,
            order_id=order_id,
            request_id=request_id,
        )

    async def list_recent_executions(
        self,
        *,
        account_id: str,
        limit: int = 20,
        request_id: str | None = None,
    ) -> list[dict[str, Any]]:
        return await self._client.list_recent_executions(
            account_id=account_id,
            limit=limit,
            request_id=request_id,
        )

    async def get_order_book(
        self,
        *,
        symbol: str,
        depth: int = 20,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        return await self._client.get_order_book(
            symbol=symbol,
            depth=depth,
            request_id=request_id,
        )

    async def health(self, request_id: str | None = None) -> dict[str, Any]:
        return await self._client.health(request_id=request_id)

    async def get_service_stats(
        self,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        return await self._client.get_service_stats(request_id=request_id)

