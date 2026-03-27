from __future__ import annotations

import pytest

from app.infrastructure import MatchingGatewayAdapter
from app.schemas import (
    MatchingExecutionView,
    MatchingHealthView,
    MatchingOrderBookView,
    MatchingOrderView,
    MatchingStatsView,
)


class FakeMatchingClient:
    enabled = True

    async def get_order(
        self,
        *,
        account_id: str,
        order_id: str,
        request_id: str | None = None,
    ) -> dict[str, object]:
        assert account_id == "acc-1"
        assert order_id == "ord-1"
        return {
            "order_id": order_id,
            "account_id": account_id,
            "symbol": "BTCUSDT",
            "side": "BUY",
            "order_type": "LIMIT",
            "price": 100.0,
            "quantity": 1.0,
            "filled_quantity": 0.25,
            "status": "OPEN",
        }

    async def list_recent_executions(
        self,
        *,
        account_id: str,
        limit: int = 20,
        request_id: str | None = None,
    ) -> list[dict[str, object]]:
        assert account_id == "acc-1"
        assert limit == 2
        return [
            {
                "execution_id": "exe-1",
                "order_id": "ord-1",
                "account_id": account_id,
                "symbol": "BTCUSDT",
                "price": 100.0,
                "quantity": 0.5,
                "event_time": "2026-03-27T10:00:00Z",
            }
        ]

    async def get_order_book(
        self,
        *,
        symbol: str,
        depth: int = 20,
        request_id: str | None = None,
    ) -> dict[str, object]:
        assert symbol == "BTCUSDT"
        assert depth == 5
        return {
            "enabled": True,
            "symbol": symbol,
            "depth": depth,
            "bids": [{"price": 100.0, "total_quantity": 1.2, "order_count": 2}],
            "asks": [{"price": 100.5, "total_quantity": 0.8, "order_count": 1}],
            "generated_at_ms": 1700000000000,
        }

    async def health(self, request_id: str | None = None) -> dict[str, object]:
        return {
            "enabled": True,
            "reachable": True,
            "status": "ok",
            "service": "matching-cpp",
            "version": "0.1.0",
            "uptime_seconds": 120,
        }

    async def get_service_stats(self, request_id: str | None = None) -> dict[str, object]:
        return {
            "enabled": True,
            "live_orders": 3,
            "trade_count": 7,
            "tracked_orders": 10,
            "rejected_orders": 1,
            "symbols": 2,
            "best_bid": 100.0,
            "best_ask": 101.0,
        }


@pytest.mark.asyncio
async def test_matching_gateway_adapter_returns_typed_query_models() -> None:
    adapter = MatchingGatewayAdapter(FakeMatchingClient())

    order = await adapter.get_order(
        account_id="acc-1",
        order_id="ord-1",
        request_id="rid-typed-order",
    )
    executions = await adapter.list_recent_executions(
        account_id="acc-1",
        limit=2,
        request_id="rid-typed-executions",
    )
    orderbook = await adapter.get_order_book(
        symbol="BTCUSDT",
        depth=5,
        request_id="rid-typed-orderbook",
    )
    health = await adapter.health(request_id="rid-typed-health")
    stats = await adapter.get_service_stats(request_id="rid-typed-stats")

    assert isinstance(order, MatchingOrderView)
    assert isinstance(executions[0], MatchingExecutionView)
    assert isinstance(orderbook, MatchingOrderBookView)
    assert isinstance(health, MatchingHealthView)
    assert isinstance(stats, MatchingStatsView)
    assert order.request_id == "rid-typed-order"
    assert executions[0].request_id == "rid-typed-executions"
    assert orderbook.request_id == "rid-typed-orderbook"
