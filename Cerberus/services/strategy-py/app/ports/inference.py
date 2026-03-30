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


@dataclass(frozen=True, slots=True)
class InferenceAuditEvent:
    event_type: str
    created_at: str
    message: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "created_at": self.created_at,
            "message": self.message,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class InferenceSymbolComparison:
    symbol: str
    compared_ticks: int
    agreement_count: int
    divergence_count: int

    @property
    def agreement_ratio(self) -> float | None:
        if self.compared_ticks <= 0:
            return None
        return self.agreement_count / self.compared_ticks

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "compared_ticks": self.compared_ticks,
            "agreement_count": self.agreement_count,
            "divergence_count": self.divergence_count,
            "agreement_ratio": self.agreement_ratio,
        }


@dataclass(frozen=True, slots=True)
class InferenceComparisonSnapshot:
    observed_ticks: int
    compared_ticks: int
    agreement_count: int
    divergence_count: int
    rule_signal_counts: dict[str, int] = field(default_factory=dict)
    inference_signal_counts: dict[str, int] = field(default_factory=dict)
    symbols: tuple[InferenceSymbolComparison, ...] = ()

    @property
    def agreement_ratio(self) -> float | None:
        if self.compared_ticks <= 0:
            return None
        return self.agreement_count / self.compared_ticks

    def to_dict(self) -> dict[str, Any]:
        return {
            "observed_ticks": self.observed_ticks,
            "compared_ticks": self.compared_ticks,
            "agreement_count": self.agreement_count,
            "divergence_count": self.divergence_count,
            "agreement_ratio": self.agreement_ratio,
            "rule_signal_counts": dict(self.rule_signal_counts),
            "inference_signal_counts": dict(self.inference_signal_counts),
            "symbols": [item.to_dict() for item in self.symbols],
        }


@dataclass(frozen=True, slots=True)
class InferenceRolloutSnapshot:
    configured_mode: str
    effective_mode: str
    auto_promote_enabled: bool
    force_primary: bool
    promotion_eligible: bool
    state_backend: str | None = None
    state_restored: bool = False
    last_persisted_at: str = ""
    blockers: tuple[str, ...] = ()
    required_observe_ticks: int = 0
    compared_ticks: int = 0
    required_agreement_ratio: float = 0.0
    agreement_ratio: float | None = None
    required_macro_f1: float = 0.0
    current_macro_f1: float | None = None
    started_at: str = ""
    last_transition_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "configured_mode": self.configured_mode,
            "effective_mode": self.effective_mode,
            "auto_promote_enabled": self.auto_promote_enabled,
            "force_primary": self.force_primary,
            "promotion_eligible": self.promotion_eligible,
            "state_backend": self.state_backend,
            "state_restored": self.state_restored,
            "last_persisted_at": self.last_persisted_at,
            "blockers": list(self.blockers),
            "required_observe_ticks": self.required_observe_ticks,
            "compared_ticks": self.compared_ticks,
            "required_agreement_ratio": self.required_agreement_ratio,
            "agreement_ratio": self.agreement_ratio,
            "required_macro_f1": self.required_macro_f1,
            "current_macro_f1": self.current_macro_f1,
            "started_at": self.started_at,
            "last_transition_at": self.last_transition_at,
        }


class ModelRegistryPort(Protocol):
    def list_models(self) -> tuple[RegisteredModel, ...]: ...

    def active_model(self) -> RegisteredModel | None: ...


class InferenceRolloutStateStorePort(Protocol):
    @property
    def backend_name(self) -> str: ...

    async def load_state(self) -> dict[str, Any] | None: ...

    async def save_state(self, state: dict[str, Any]) -> None: ...


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


class InferenceRolloutPort(Protocol):
    async def restore(self) -> None: ...

    def effective_mode(self) -> str: ...

    async def record_observation(
        self,
        *,
        symbol: str,
        rule_signal: str,
        inference_decision: InferenceDecision | None,
    ) -> None: ...

    def snapshot(self) -> InferenceRolloutSnapshot: ...

    def comparison(self) -> InferenceComparisonSnapshot: ...

    def recent_audit_events(self, *, limit: int = 10) -> tuple[InferenceAuditEvent, ...]: ...

    async def flush(self) -> None: ...
