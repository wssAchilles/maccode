from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class InferenceDecision:
    strategy_id: str
    signal: str
    confidence: float
    engine: str
    model_id: str | None = None
    model_version: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RegisteredModel:
    model_id: str
    version: str
    source: str
    task: str = "signal_inference"
    symbols: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "version": self.version,
            "source": self.source,
            "task": self.task,
            "symbols": list(self.symbols),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class InferenceEngineStatus:
    enabled: bool
    ready: bool
    engine: str
    mode: str
    reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "ready": self.ready,
            "engine": self.engine,
            "mode": self.mode,
            "reason": self.reason,
            "metadata": dict(self.metadata),
        }


class ModelRegistryPort(Protocol):
    def list_models(self) -> tuple[RegisteredModel, ...]: ...

    def active_model(self) -> RegisteredModel | None: ...


class InferenceEnginePort(Protocol):
    async def infer_signal(
        self,
        *,
        symbol: str,
        price: float,
        quantity: float,
        event_time: str,
    ) -> InferenceDecision | None: ...

    async def status(self) -> InferenceEngineStatus: ...
