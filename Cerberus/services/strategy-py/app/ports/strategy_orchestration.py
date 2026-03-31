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
    metadata: dict[str, Any] = field(default_factory=dict)

    def configured_weight(self, *, mode: str) -> float:
        if mode == "primary":
            return self.primary_weight
        return self.observe_weight

    def covers_symbol(self, symbol: str) -> bool:
        return not self.symbol_coverage or symbol in self.symbol_coverage


@dataclass(frozen=True, slots=True)
class StrategyOrchestrationSnapshot:
    conflict_policy: str
    downgrade_policy: str
    tracked_symbols: tuple[str, ...]
    state_backend: str | None
    state_restored: bool
    entries: tuple[StrategyOrchestrationEntry, ...]


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
