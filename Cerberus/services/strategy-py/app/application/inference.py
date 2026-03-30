from __future__ import annotations

from dataclasses import dataclass

from app.ports import (
    InferenceEnginePort,
    InferenceEngineStatus,
    ModelRegistryPort,
    RegisteredModel,
)


@dataclass(frozen=True, slots=True)
class InferenceStatusResult:
    engine_status: InferenceEngineStatus
    active_model: RegisteredModel | None

    def to_dict(self) -> dict[str, object]:
        payload = self.engine_status.to_dict()
        payload["active_model"] = None if self.active_model is None else self.active_model.to_dict()
        return payload


@dataclass(frozen=True, slots=True)
class InferenceCatalogResult:
    active_model: RegisteredModel | None
    models: tuple[RegisteredModel, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "count": len(self.models),
            "active_model": None if self.active_model is None else self.active_model.to_dict(),
            "models": [item.to_dict() for item in self.models],
        }


class InferenceApplicationService:
    def __init__(
        self,
        *,
        engine: InferenceEnginePort,
        model_registry: ModelRegistryPort,
    ) -> None:
        self._engine = engine
        self._model_registry = model_registry

    async def status(self) -> InferenceStatusResult:
        return InferenceStatusResult(
            engine_status=await self._engine.status(),
            active_model=self._model_registry.active_model(),
        )

    def models(self) -> InferenceCatalogResult:
        return InferenceCatalogResult(
            active_model=self._model_registry.active_model(),
            models=self._model_registry.list_models(),
        )
