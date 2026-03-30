from __future__ import annotations

import pytest

from app.application.inference import InferenceApplicationService
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
