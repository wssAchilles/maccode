from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.ports import (
    InferenceDecision,
    InferenceEnginePort,
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
        inference_engine: InferenceEnginePort | None = None,
        inference_mode: str = "disabled",
    ) -> None:
        self._runtime = runtime
        self._signal_store = signal_store
        self._signal_claims = signal_claims
        self._event_flow = event_flow
        self._publishers = publishers
        self._default_engine_name = default_engine_name
        self._inference_engine = inference_engine
        self._inference_mode = inference_mode

    def current_signal(self) -> SignalDecision | None:
        signal = self._runtime.read_current_signal()
        if signal is None:
            return None
        return self._build_decision(signal)

    async def ingest_tick(self, tick: TickEvent) -> SignalDecision:
        rule_signal, rule_signal_id = self._runtime.evaluate_tick(tick)
        inference_decision = await self._run_inference(tick)

        signal = rule_signal
        signal_id = rule_signal_id
        engine_name = self._default_engine_name
        metadata = self._decision_metadata(
            tick,
            signal_id=signal_id,
            dispatch_state="accepted",
            inference_decision=inference_decision,
        )
        if inference_decision is not None and self._inference_mode == "primary":
            signal = Signal(
                strategy_id=inference_decision.strategy_id,
                symbol=tick.symbol,
                signal=inference_decision.signal,
                confidence=inference_decision.confidence,
            )
            signal_id = self._runtime.build_signal_id(tick, signal)
            engine_name = inference_decision.engine
            metadata["signal_id"] = signal_id
            metadata["decision_source"] = "inference"

        if not await self._signal_claims.claim_signal(signal_id):
            return self._build_decision(
                signal,
                metadata=self._decision_metadata(
                    tick,
                    signal_id=signal_id,
                    dispatch_state="duplicate",
                    inference_decision=inference_decision,
                ),
                engine=engine_name,
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
            metadata=metadata,
            engine=engine_name,
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
        engine: str | None = None,
    ) -> SignalDecision:
        return SignalDecision(
            signal=signal,
            context=SignalDecisionContext(
                engine=engine or self._default_engine_name,
                metadata=metadata or {},
            ),
        )

    def _decision_metadata(
        self,
        tick: TickEvent,
        *,
        signal_id: str,
        dispatch_state: str,
        inference_decision: InferenceDecision | None = None,
    ) -> dict[str, Any]:
        payload = {
            "event_time": tick.event_time,
            "price": tick.price,
            "quantity": tick.quantity,
            "signal_id": signal_id,
            "dispatch_state": dispatch_state,
            "decision_source": "rule_engine",
        }
        if inference_decision is not None:
            payload["inference"] = {
                "engine": inference_decision.engine,
                "signal": inference_decision.signal,
                "confidence": inference_decision.confidence,
                "model_id": inference_decision.model_id,
                "model_version": inference_decision.model_version,
                "metadata": dict(inference_decision.metadata),
            }
        return payload

    async def _run_inference(self, tick: TickEvent) -> InferenceDecision | None:
        if self._inference_engine is None or self._inference_mode == "disabled":
            return None
        return await self._inference_engine.infer_signal(
            symbol=tick.symbol,
            price=tick.price,
            quantity=tick.quantity,
            event_time=tick.event_time,
        )
