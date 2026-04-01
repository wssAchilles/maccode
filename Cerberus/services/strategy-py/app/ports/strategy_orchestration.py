from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class StrategyOrchestrationEntry:
    strategy_id: str
    label: str
    engine: str
    source: str
    role: str
    enabled: bool
    priority: int
    observe_weight: float
    primary_weight: float
    symbol_coverage: tuple[str, ...] = ()
    conflict_targets: tuple[str, ...] = ()
    downgrade_action: str = "review"
    metadata: dict[str, Any] = field(default_factory=dict)

    def configured_weight(self, *, mode: str) -> float:
        if mode == "primary":
            return self.primary_weight
        return self.observe_weight

    def covers_symbol(self, symbol: str) -> bool:
        return not self.symbol_coverage or symbol in self.symbol_coverage


@dataclass(frozen=True, slots=True)
class StrategyOrchestrationAuditEvent:
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
class StrategyOrchestrationSnapshot:
    conflict_policy: str
    downgrade_policy: str
    tracked_symbols: tuple[str, ...]
    state_backend: str | None
    state_restored: bool
    entries: tuple[StrategyOrchestrationEntry, ...]
    audit: tuple[StrategyOrchestrationAuditEvent, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "conflict_policy": self.conflict_policy,
            "downgrade_policy": self.downgrade_policy,
            "tracked_symbols": list(self.tracked_symbols),
            "state_backend": self.state_backend,
            "state_restored": self.state_restored,
            "entries": [
                {
                    "strategy_id": item.strategy_id,
                    "label": item.label,
                    "engine": item.engine,
                    "source": item.source,
                    "role": item.role,
                    "enabled": item.enabled,
                    "priority": item.priority,
                    "observe_weight": item.observe_weight,
                    "primary_weight": item.primary_weight,
                    "symbol_coverage": list(item.symbol_coverage),
                    "conflict_targets": list(item.conflict_targets),
                    "downgrade_action": item.downgrade_action,
                    "metadata": dict(item.metadata),
                }
                for item in self.entries
            ],
            "audit": [item.to_dict() for item in self.audit],
        }


@dataclass(frozen=True, slots=True)
class StrategyOrchestrationControlResult:
    accepted: bool
    action: str
    message: str
    actor: str | None = None
    reason: str | None = None
    snapshot: StrategyOrchestrationSnapshot | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "accepted": self.accepted,
            "action": self.action,
            "message": self.message,
            "actor": self.actor,
            "reason": self.reason,
            "snapshot": None if self.snapshot is None else self.snapshot.to_dict(),
        }


class StrategyOrchestrationPort(Protocol):
    async def startup(self) -> None: ...

    async def shutdown(self) -> None: ...

    def snapshot(
        self,
        *,
        tracked_symbols: tuple[str, ...],
        inference_runtime_enabled: bool,
        inference_model_symbols: tuple[str, ...] = (),
        inference_engine_name: str | None = None,
    ) -> StrategyOrchestrationSnapshot: ...

    def audit(self, *, limit: int = 20) -> tuple[StrategyOrchestrationAuditEvent, ...]: ...

    async def update_entry(
        self,
        *,
        strategy_id: str,
        tracked_symbols: tuple[str, ...],
        inference_runtime_enabled: bool,
        inference_model_symbols: tuple[str, ...] = (),
        inference_engine_name: str | None = None,
        enabled: bool | None = None,
        priority: int | None = None,
        observe_weight: float | None = None,
        primary_weight: float | None = None,
        symbol_coverage: tuple[str, ...] | None = None,
        conflict_targets: tuple[str, ...] | None = None,
        downgrade_action: str | None = None,
        actor: str | None = None,
        reason: str | None = None,
    ) -> StrategyOrchestrationControlResult: ...

    async def update_policies(
        self,
        *,
        tracked_symbols: tuple[str, ...],
        inference_runtime_enabled: bool,
        inference_model_symbols: tuple[str, ...] = (),
        inference_engine_name: str | None = None,
        conflict_policy: str | None = None,
        downgrade_policy: str | None = None,
        actor: str | None = None,
        reason: str | None = None,
    ) -> StrategyOrchestrationControlResult: ...
