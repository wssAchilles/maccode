from __future__ import annotations

import pytest

from app.event_runtime.relay import build_execution_publish_batch


class FakeRelayWorker:
    def __init__(self) -> None:
        self.last_execution_id = 1
        self.claimed_order_ids: list[str] = []
        self.claimable_orders = {"o-2": True, "o-3": False}

    async def claim_order(self, order_id: str) -> bool:
        self.claimed_order_ids.append(order_id)
        return self.claimable_orders.get(order_id, True)


@pytest.mark.asyncio
async def test_build_execution_publish_batch_sorts_filters_and_claims() -> None:
    worker = FakeRelayWorker()
    items = [
        {
            "execution_id": "3",
            "order_id": "o-3",
            "symbol": "ETHUSDT",
            "price": 3000.0,
            "quantity": 0.5,
            "event_time": "2026-03-27T10:01:00Z",
        },
        {
            "execution_id": "2",
            "order_id": "o-2",
            "symbol": "BTCUSDT",
            "price": 100.0,
            "quantity": 1.0,
            "event_time": "2026-03-27T10:00:00Z",
        },
        {
            "execution_id": "1",
            "order_id": "o-1",
            "symbol": "BTCUSDT",
            "price": 90.0,
            "quantity": 0.8,
            "event_time": "2026-03-27T09:59:00Z",
        },
    ]

    publish_batch, claimed_order_ids, next_last_execution_id = await build_execution_publish_batch(
        worker,
        "cerberus.trade.executions.default",
        items,
    )

    assert next_last_execution_id == 3
    assert worker.claimed_order_ids == ["o-2", "o-3"]
    assert claimed_order_ids == ["o-2"]
    assert len(publish_batch) == 1
    event = publish_batch[0]
    assert event.channel == "cerberus.trade.executions.default"
    assert event.event_type == "matching.execution.filled"
    assert event.correlation_id == "o-2"
    assert event.payload["execution_id"] == "2"
    assert event.payload["symbol"] == "BTCUSDT"
