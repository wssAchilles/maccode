from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.ports import (
    SignalClaimPort,
    SignalEventPort,
    SignalHistorySource,
    SignalPublisherPort,
    SignalRuntimePort,
    SignalStorePort,
    SignalStoreSource,
)
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
        signal_claims: SignalClaimPort,
        event_flow: SignalEventPort,
        publishers: tuple[SignalPublisherPort, ...] = (),
        default_engine_name: str = "moving_average",
    ) -> None:
        self._runtime = runtime
        self._signal_store = signal_store
        self._signal_claims = signal_claims
        self._event_flow = event_flow
        self._publishers = publishers
        self._default_engine_name = default_engine_name

    def current_signal(self) -> SignalDecision | None:
        signal = self._runtime.read_current_signal()
        if signal is None:
            return None
        return self._build_decision(signal)

    async def ingest_tick(self, tick: TickEvent) -> SignalDecision:
        signal, signal_id = self._runtime.evaluate_tick(tick)
        if not await self._signal_claims.claim_signal(signal_id):
            return self._build_decision(
                signal,
                metadata=self._decision_metadata(
                    tick,
                    signal_id=signal_id,
                    dispatch_state="duplicate",
                ),
            )

        try:
            self._runtime.store_current_signal(signal)
            await self._event_flow.publish_signal_flow(signal, tick, signal_id)
            for publisher in self._publishers:
                await publisher.publish_signal(signal)
        except Exception:
            await self._signal_claims.release_signal_claim(signal_id)
            raise

        self._runtime.record_tick_processed()
        return self._build_decision(
            signal,
            metadata=self._decision_metadata(
                tick,
                signal_id=signal_id,
                dispatch_state="accepted",
            ),
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

    def _decision_metadata(
        self,
        tick: TickEvent,
        *,
        signal_id: str,
        dispatch_state: str,
    ) -> dict[str, Any]:
        return {
            "event_time": tick.event_time,
            "price": tick.price,
            "quantity": tick.quantity,
            "signal_id": signal_id,
            "dispatch_state": dispatch_state,
        }
