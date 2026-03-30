from __future__ import annotations

import pytest

from app.application.inference import InferenceApplicationService
from app.infrastructure.inference_rollout import RuntimeInferenceRolloutManager
from app.infrastructure.inference_runtime import DisabledInferenceEngine, StaticModelRegistry
from app.ports import RegisteredModel


@pytest.mark.asyncio
async def test_inference_application_returns_disabled_status_without_models() -> None:
    service = InferenceApplicationService(
        engine=DisabledInferenceEngine(),
        model_registry=StaticModelRegistry(models=()),
    )

    status = await service.status()

    assert status.engine_status.enabled is False
    assert status.active_model is None
    assert status.rollout.effective_mode == "disabled"
    assert status.comparison.compared_ticks == 0


def test_inference_application_lists_registered_models() -> None:
    registry = StaticModelRegistry(
        models=(
            RegisteredModel(
                model_id="moving-average-baseline",
                version="v1",
                source="runtime",
                symbols=("BTCUSDT", "ETHUSDT"),
            ),
        ),
        active_model_id="moving-average-baseline",
    )
    service = InferenceApplicationService(
        engine=DisabledInferenceEngine(),
        model_registry=registry,
    )

    catalog = service.models()

    assert catalog.active_model is not None
    assert catalog.active_model.model_id == "moving-average-baseline"
    assert catalog.models[0].symbols == ("BTCUSDT", "ETHUSDT")


@pytest.mark.asyncio
async def test_inference_application_promote_returns_gate_held_control_result() -> None:
    registry = StaticModelRegistry(
        models=(
            RegisteredModel(
                model_id="cerberus-transformer-lstm",
                version="v1",
                source="gcs",
                symbols=("BTCUSDT",),
                metadata={"best_macro_f1": 0.5},
            ),
        ),
        active_model_id="cerberus-transformer-lstm",
        active_model_version="v1",
    )
    rollout = RuntimeInferenceRolloutManager(
        configured_mode="observe",
        active_model=registry.active_model(),
        started_at=1_711_767_200.0,
        required_macro_f1=0.58,
        required_observe_ticks=10,
        required_agreement_ratio=0.55,
        force_primary=False,
    )
    service = InferenceApplicationService(
        engine=DisabledInferenceEngine(),
        model_registry=registry,
        rollout=rollout,
    )

    result = await service.promote(actor="operator@example.com", reason="attempt promotion")

    assert result.action == "promote"
    assert result.accepted is False
    assert result.rollout.target_mode == "primary"
    assert result.rollout.effective_mode == "observe"


@pytest.mark.asyncio
async def test_inference_application_activate_model_updates_registry_and_rollout() -> None:
    registry = StaticModelRegistry(
        models=(
            RegisteredModel(
                model_id="cerberus-transformer-lstm",
                version="v1",
                source="gcs",
                symbols=("BTCUSDT",),
                metadata={"best_macro_f1": 0.50},
            ),
            RegisteredModel(
                model_id="cerberus-transformer-lstm",
                version="v2",
                source="gcs",
                symbols=("BTCUSDT", "ETHUSDT"),
                metadata={"best_macro_f1": 0.68},
            ),
        ),
        active_model_id="cerberus-transformer-lstm",
        active_model_version="v1",
    )
    rollout = RuntimeInferenceRolloutManager(
        configured_mode="observe",
        active_model=registry.active_model(),
        started_at=1_711_767_200.0,
        required_macro_f1=0.58,
        required_observe_ticks=10,
        required_agreement_ratio=0.55,
        force_primary=False,
    )
    service = InferenceApplicationService(
        engine=DisabledInferenceEngine(),
        model_registry=registry,
        rollout=rollout,
    )

    result = await service.activate_model(
        model_id="cerberus-transformer-lstm",
        version="v2",
        actor="operator@example.com",
        reason="switch to v2",
    )

    assert result.action == "activate_model"
    assert result.accepted is True
    assert result.active_model is not None
    assert result.active_model.version == "v2"
    assert result.selected_model is not None
    assert result.selected_model.version == "v2"
