from fastapi.testclient import TestClient

from app import main as main_module
from app.application import InferenceStatusResult
from app.main import app
from app.ports import (
    InferenceComparisonSnapshot,
    InferenceEngineStatus,
    InferenceRolloutSnapshot,
    RegisteredModel,
)
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

    async def fake_inference_status() -> InferenceStatusResult:
        return InferenceStatusResult(
            engine_status=InferenceEngineStatus(
                enabled=True,
                ready=True,
                engine="cerberus_signal_transformer_lstm",
                mode="observe",
                metadata={"lookback": 256},
            ),
            active_model=RegisteredModel(
                model_id="cerberus-transformer-lstm",
                version="v1",
                source="gcs",
                symbols=("BTCUSDT", "ETHUSDT"),
                metadata={"best_macro_f1": 0.5001, "horizon": 32},
            ),
            rollout=InferenceRolloutSnapshot(
                configured_mode="primary",
                target_mode="primary",
                effective_mode="observe",
                override_active=False,
                auto_promote_enabled=True,
                force_primary=False,
                promotion_eligible=False,
                blockers=("offline_macro_f1_below_threshold",),
                required_observe_ticks=500,
                compared_ticks=24,
                required_agreement_ratio=0.55,
                agreement_ratio=0.5,
                required_macro_f1=0.58,
                current_macro_f1=0.5001,
                started_at="2026-03-30T00:00:00Z",
                last_transition_at="2026-03-30T00:00:00Z",
            ),
            comparison=InferenceComparisonSnapshot(
                observed_ticks=30,
                compared_ticks=24,
                agreement_count=12,
                divergence_count=12,
            ),
        )

    main_module.inference_service._application.status = fake_inference_status  # type: ignore[method-assign, attr-defined]

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
    assert payload["inference_status"]["payload"]["mode"] == "observe"
    assert payload["inference_status"]["payload"]["active_model"]["model_id"] == "cerberus-transformer-lstm"
    assert payload["inference_status"]["payload"]["rollout"]["configured_mode"] == "primary"
    assert payload["inference_status"]["payload"]["comparison"]["compared_ticks"] == 24


def test_strategy_summary_inference_status_matches_standalone_endpoint_shape() -> None:
    client = TestClient(app)
    direct = client.get("/api/v1/inference/status")
    summary = client.get("/api/v1/summary")

    assert direct.status_code == 200
    assert summary.status_code == 200
    assert summary.json()["inference_status"]["payload"] == direct.json()
