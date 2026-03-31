from __future__ import annotations

from typing import Any, Literal

from app.application import SignalApplicationService, SignalDecision
from app.schemas import TickEvent

SignalSource = Literal["auto", "supabase", "firestore"]


class SignalService:
    def __init__(self, *, application: SignalApplicationService) -> None:
        self._application = application

    async def startup(self) -> None:
        await self._application.startup()

    async def shutdown(self) -> None:
        await self._application.shutdown()

    def current_signal(self) -> dict[str, Any]:
        decision = self._application.current_signal()
        if decision is None:
            return {"status": "warmup", "signal": "HOLD", "confidence": 0.0}
        return self._ready_signal_payload(decision)

    async def ingest_tick(self, tick: TickEvent) -> dict[str, Any]:
        decision = await self._application.ingest_tick(tick)
        return {
            "status": "accepted",
            "signal": decision.signal.signal,
            "confidence": decision.signal.confidence,
            "symbol": decision.signal.symbol,
            "strategy_id": decision.signal.strategy_id,
        }

    async def recent_signals(self, *, limit: int, source: str) -> dict[str, Any]:
        normalized_source = self._normalize_source(source)
        used_source, records = await self._application.recent_signals(
            limit=limit,
            source=normalized_source,
        )
        return {
            "source": used_source,
            "count": len(records),
            "signals": [item.model_dump() for item in records],
        }

    def _normalize_source(self, source: str) -> SignalSource:
        if source == "supabase":
            return "supabase"
        if source == "firestore":
            return "firestore"
        return "auto"

    def _ready_signal_payload(self, decision: SignalDecision) -> dict[str, Any]:
        payload = {
            "status": "ready",
            "signal": decision.signal.signal,
            "confidence": decision.signal.confidence,
            "symbol": decision.signal.symbol,
            "strategy_id": decision.signal.strategy_id,
            "engine": decision.context.engine,
        }
        for key in (
            "decision_source",
            "dispatch_state",
            "inference_mode",
            "signal_id",
            "strategy_basket",
            "portfolio",
            "strategy_registry",
        ):
            if key in decision.context.metadata:
                payload[key] = decision.context.metadata[key]
        return payload
