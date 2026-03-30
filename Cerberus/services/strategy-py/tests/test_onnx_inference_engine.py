from __future__ import annotations

from pathlib import Path

import pytest

from app.infrastructure.inference_artifacts import (
    InferencePreprocessing,
    LoadedInferenceArtifacts,
)
from app.infrastructure.inference_runtime import OnnxInferenceEngine
from app.ports import RegisteredModel


class FakeSession:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def run(self, _outputs: object, inputs: dict[str, object]) -> list[object]:
        self.calls.append(inputs)
        return [[[0.1, 0.2, 0.7]]]


@pytest.mark.asyncio
async def test_onnx_inference_engine_warms_up_before_emitting_decision(tmp_path: Path) -> None:
    session = FakeSession()
    artifacts = LoadedInferenceArtifacts(
        manifest={
            "signals": {"0": "SELL", "1": "HOLD", "2": "BUY"},
            "strategy_id": "inference",
        },
        metrics={"best_macro_f1": 0.5},
        preprocessing=InferencePreprocessing(
            feature_columns=(
                "log_ret_1",
                "ret_1",
                "ret_3",
                "ret_8",
                "ret_21",
                "log_quantity",
                "ema_gap_8",
                "ema_gap_21",
                "ema_cross_8_21",
                "ema_cross_21_55",
                "vol_8",
                "vol_21",
                "qty_z_21",
                "notional_z_21",
            ),
            feature_mean=tuple(0.0 for _ in range(14)),
            feature_std=tuple(1.0 for _ in range(14)),
            symbol_to_id={"BTCUSDT": 0},
            lookback=2,
        ),
        onnx_path=tmp_path / "model.onnx",
        training_bundle_path=tmp_path / "bundle.pt",
        cache_dir=tmp_path,
    )
    model = RegisteredModel(
        model_id="cerberus-transformer-lstm",
        version="v1",
        source="google_drive",
        symbols=("BTCUSDT",),
    )
    engine = OnnxInferenceEngine(
        engine_name="cerberus_signal_transformer_lstm",
        mode="observe",
        model=model,
        artifacts=artifacts,
        session=session,
    )

    decision = None
    for index in range(22):
        decision = await engine.infer_signal(
            symbol="BTCUSDT",
            price=100.0 + index,
            quantity=1.0 + (index * 0.1),
            event_time="2026-03-30T00:00:00Z",
        )
        assert decision is None

    decision = await engine.infer_signal(
        symbol="BTCUSDT",
        price=122.0,
        quantity=3.2,
        event_time="2026-03-30T00:00:01Z",
    )

    assert decision is not None
    assert decision.signal == "BUY"
    assert decision.strategy_id == "inference"
    assert decision.model_id == "cerberus-transformer-lstm"
    assert session.calls
    first_call = session.calls[0]
    assert getattr(first_call["features"], "shape", None) == (1, 2, 14)
    assert getattr(first_call["symbol_ids"], "tolist", lambda: [])() == [0]
