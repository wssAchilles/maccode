from __future__ import annotations

from typing import Any, Protocol


class MatchingGatewayPort(Protocol):
    @property
    def enabled(self) -> bool: ...

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
    ) -> dict[str, Any]: ...

    async def cancel_order(
        self,
        *,
        account_id: str,
        order_id: str,
        request_id: str | None = None,
    ) -> dict[str, Any]: ...

    async def get_order(
        self,
        *,
        account_id: str,
        order_id: str,
        request_id: str | None = None,
    ) -> dict[str, Any]: ...

    async def list_recent_executions(
        self,
        *,
        account_id: str,
        limit: int = 20,
        request_id: str | None = None,
    ) -> list[dict[str, Any]]: ...

    async def get_order_book(
        self,
        *,
        symbol: str,
        depth: int = 20,
        request_id: str | None = None,
    ) -> dict[str, Any]: ...

    async def health(self, request_id: str | None = None) -> dict[str, Any]: ...

    async def get_service_stats(
        self,
        request_id: str | None = None,
    ) -> dict[str, Any]: ...

