from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.ports import SignalHistorySource, SignalRuntimePort, SignalStorePort, SignalStoreSource
from app.schemas import Signal, SignalRecord, TickEvent


@dataclass(frozen=True, slots=True)
class SignalDecisionContext:
    engine: str
    version: str = "v1"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SignalDecision:
    signal: Signal
    context: SignalDecisionContext


class SignalApplicationService:
    def __init__(
        self,
        *,
        runtime: SignalRuntimePort,
        signal_store: SignalStorePort,
        default_engine_name: str = "moving_average",
    ) -> None:
        self._runtime = runtime
        self._signal_store = signal_store
        self._default_engine_name = default_engine_name

    def current_signal(self) -> SignalDecision | None:
        signal = self._runtime.read_current_signal()
        if signal is None:
            return None
        return self._build_decision(signal)

    async def ingest_tick(self, tick: TickEvent) -> SignalDecision:
        signal = await self._runtime.ingest_tick(tick)
        return self._build_decision(
            signal,
            metadata={
                "event_time": tick.event_time,
                "price": tick.price,
                "quantity": tick.quantity,
            },
        )

    async def recent_signals(
        self,
        *,
        limit: int,
        source: SignalHistorySource,
    ) -> tuple[SignalStoreSource, list[SignalRecord]]:
        return await self._signal_store.list_recent(limit=limit, source=source)

    def _build_decision(
        self,
        signal: Signal,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> SignalDecision:
        return SignalDecision(
            signal=signal,
            context=SignalDecisionContext(
                engine=self._default_engine_name,
                metadata=metadata or {},
            ),
        )
