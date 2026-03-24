from __future__ import annotations

from typing import Any

from app.config import settings
from app import order_client_ops
from app.order_client_rpc import MatchingRpcTransport
from app.schemas import Signal


class MatchingOrderClient:
    def __init__(self) -> None:
        self._enabled = settings.matching_enabled and bool(settings.matching_grpc_target.strip())
        self._transport = MatchingRpcTransport(settings.matching_grpc_target)

    @property
    def enabled(self) -> bool:
        return self._enabled

    async def aclose(self) -> None:
        await self._transport.close()

    async def submit_from_signal(self, signal: Signal, price: float) -> dict[str, Any] | None:
        if not self._enabled:
            return None
        if signal.signal not in ("BUY", "SELL"):
            return None
        if price <= 0:
            return None

        result = await self.submit_limit_order(
            account_id=settings.strategy_account_id,
            symbol=signal.symbol,
            side=signal.signal,
            price=price,
            quantity=settings.strategy_order_quantity,
            client_order_id="",
        )
        result["signal"] = signal.signal
        return result

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
    ) -> dict[str, Any]:
        return await order_client_ops.submit_limit_order(
            enabled=self._enabled,
            transport=self._transport,
            account_id=account_id,
            symbol=symbol,
            side=side,
            price=price,
            quantity=quantity,
            client_order_id=client_order_id,
            request_id=request_id,
        )

    async def cancel_order(
        self, *, account_id: str, order_id: str, request_id: str | None = None
    ) -> dict[str, Any]:
        return await order_client_ops.cancel_order(
            enabled=self._enabled,
            transport=self._transport,
            account_id=account_id,
            order_id=order_id,
            request_id=request_id,
        )

    async def get_order(
        self, *, account_id: str, order_id: str, request_id: str | None = None
    ) -> dict[str, Any]:
        return await order_client_ops.get_order(
            enabled=self._enabled,
            transport=self._transport,
            account_id=account_id,
            order_id=order_id,
            request_id=request_id,
        )

    async def list_recent_executions(
        self, *, account_id: str, limit: int = 20, request_id: str | None = None
    ) -> list[dict[str, Any]]:
        return await order_client_ops.list_recent_executions(
            enabled=self._enabled,
            transport=self._transport,
            account_id=account_id,
            limit=limit,
            request_id=request_id,
        )

    async def get_order_book(
        self, *, symbol: str, depth: int = 20, request_id: str | None = None
    ) -> dict[str, Any]:
        return await order_client_ops.get_order_book(
            enabled=self._enabled,
            transport=self._transport,
            symbol=symbol,
            depth=depth,
            request_id=request_id,
        )

    async def health(self, request_id: str | None = None) -> dict[str, Any]:
        return await order_client_ops.health(
            enabled=self._enabled,
            transport=self._transport,
            request_id=request_id,
        )

    async def get_service_stats(self, request_id: str | None = None) -> dict[str, Any]:
        return await order_client_ops.get_service_stats(
            enabled=self._enabled,
            transport=self._transport,
            request_id=request_id,
        )
