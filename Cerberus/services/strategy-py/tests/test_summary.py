from fastapi.testclient import TestClient

from app import main as main_module
from app.main import app
from app.schemas import Signal, SignalRecord


def test_strategy_summary_endpoint_aggregates_components() -> None:
    async def fake_list_recent(limit: int, source: str = "auto") -> tuple[str, list[SignalRecord]]:
        assert limit == 1
        assert source == "supabase"
        return (
            "supabase",
            [
                SignalRecord(
                    strategy_id="default",
                    symbol="BTCUSDT",
                    signal="BUY",
                    confidence=0.82,
                    created_at="2026-03-27T10:00:00Z",
                )
            ],
        )

    async def fake_orderbook(
        *,
        symbol: str,
        depth: int = 20,
        request_id: str | None = None,
    ) -> dict[str, object]:
        assert symbol == "BTCUSDT"
        assert depth == 5
        assert request_id == "rid-summary-001"
        return {
            "enabled": True,
            "symbol": symbol,
            "depth": depth,
            "bids": [{"price": 100.0, "total_quantity": 1.2, "order_count": 2}],
            "asks": [{"price": 100.5, "total_quantity": 0.8, "order_count": 1}],
            "generated_at_ms": 1700000000000,
            "request_id": request_id,
        }

    main_module.worker.last_signal = Signal(
        strategy_id="default",
        symbol="BTCUSDT",
        signal="BUY",
        confidence=0.91,
    )
    main_module.signal_store.list_recent = fake_list_recent  # type: ignore[method-assign]
    main_module.worker.matching_client._enabled = True  # type: ignore[attr-defined]
    main_module.worker.matching_client.get_order_book = fake_orderbook  # type: ignore[method-assign]

    client = TestClient(app)
    response = client.get(
        "/api/v1/summary?symbol=BTCUSDT&recent_limit=1&source=supabase&orderbook_depth=5",
        headers={"x-request-id": "rid-summary-001"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "BTCUSDT"
    assert payload["source"] == "supabase"
    assert payload["signal"]["ok"] is True
    assert payload["signal"]["payload"]["signal"] == "BUY"
    assert payload["recent_signals"]["payload"]["count"] == 1
    assert payload["matching_orderbook"]["payload"]["depth"] == 5
    assert "persistence" in payload
