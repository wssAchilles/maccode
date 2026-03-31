from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

from app.schemas import Signal, SignalRecord, TickEvent

SignalHistorySource = Literal["auto", "supabase", "firestore"]
SignalStoreSource = Literal["supabase", "firestore", "none"]


@dataclass(frozen=True, slots=True)
class StrategyDecisionSnapshot:
    strategy_id: str
    label: str
    engine: str
    signal: str
    confidence: float
    weight: float
    priority: int
    role: str
    active: bool
    source: str
    reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class StrategyRegistryEntrySnapshot:
    strategy_id: str
    label: str
    engine: str
    source: str
    role: str
    enabled: bool
    priority: int
    configured_weight: float
    effective_weight: float
    symbol_coverage: tuple[str, ...] = ()
    conflict_policy: str = "review_on_conflict"
    downgrade_policy: str = "review"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class StrategyRegistrySnapshot:
    symbol: str
    tracked_symbols: tuple[str, ...]
    conflict_policy: str
    downgrade_policy: str
    entries: tuple[StrategyRegistryEntrySnapshot, ...] = ()


@dataclass(frozen=True, slots=True)
class PortfolioSignalSnapshot:
    symbol: str
    dominant_signal: str
    final_signal: str
    final_source: str
    signal_bias: str
    consensus_level: str
    execution_ready: bool
    execution_gate: str
    execution_gate_reason: str
    lead_strategy_id: str | None
    lead_strategy_label: str | None
    aligned_count: int
    contested_count: int
    agreement_ratio: float | None
    weighted_score: float
    active_strategy_count: int
    tracked_symbols: tuple[str, ...]
    updated_at: str | None
    latest_price: float | None


@dataclass(frozen=True, slots=True)
class SignalDecisionSnapshot:
    signal: Signal
    engine: str
    signal_id: str
    dispatch_state: str
    decision_source: str
    inference_mode: str
    strategies: tuple[StrategyDecisionSnapshot, ...]
    portfolio: PortfolioSignalSnapshot
    registry: StrategyRegistrySnapshot | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class SignalRuntimePort(Protocol):
    def read_current_signal(self) -> Signal | None: ...

    def read_current_decision(self) -> SignalDecisionSnapshot | None: ...

    def evaluate_tick(self, tick: TickEvent) -> tuple[Signal, str]: ...

    def build_signal_id(self, tick: TickEvent, signal: Signal) -> str: ...

    def store_current_signal(self, signal: Signal) -> None: ...

    def store_current_decision(self, decision: SignalDecisionSnapshot) -> None: ...

    def tracked_symbols(self) -> tuple[str, ...]: ...

    def record_tick_processed(self) -> None: ...


class SignalClaimPort(Protocol):
    async def claim_signal(self, signal_id: str) -> bool: ...

    async def release_signal_claim(self, signal_id: str) -> None: ...


class SignalEventPort(Protocol):
    async def publish_signal_flow(
        self,
        signal: Signal,
        tick: TickEvent,
        signal_id: str,
    ) -> None: ...


class SignalStorePort(Protocol):
    async def list_recent(
        self,
        limit: int,
        source: SignalHistorySource = "auto",
    ) -> tuple[SignalStoreSource, list[SignalRecord]]: ...


class SignalPublisherPort(Protocol):
    async def publish_signal(self, signal: Signal) -> None: ...
