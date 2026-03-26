from __future__ import annotations

from typing import Any, Literal

from app.redis_worker import RedisMarketWorker
from app.schemas import TickEvent
from app.signal_store import SignalStore

SignalSource = Literal["auto", "supabase", "firestore"]


class SignalService:
    def __init__(self, *, worker: RedisMarketWorker, signal_store: SignalStore) -> None:
        self._worker = worker
        self._signal_store = signal_store

    def current_signal(self) -> dict[str, Any]:
        if self._worker.last_signal is None:
            return {"status": "warmup", "signal": "HOLD", "confidence": 0.0}
        return {
            "status": "ready",
            "signal": self._worker.last_signal.signal,
            "confidence": self._worker.last_signal.confidence,
            "symbol": self._worker.last_signal.symbol,
        }

    async def ingest_tick(self, tick: TickEvent) -> dict[str, Any]:
        signal = await self._worker.ingest_tick(tick)
        return {
            "status": "accepted",
            "signal": signal.signal,
            "confidence": signal.confidence,
            "symbol": signal.symbol,
            "strategy_id": signal.strategy_id,
        }

    async def recent_signals(self, *, limit: int, source: str) -> dict[str, Any]:
        normalized_source = self._normalize_source(source)
        used_source, records = await self._signal_store.list_recent(
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
