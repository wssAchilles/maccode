from typing import Any, Literal

from fastapi import APIRouter, Query

from app.config import settings
from app.redis_worker import RedisMarketWorker
from app.schemas import TickEvent
from app.signal_store import SignalStore


def build_signal_router(worker: RedisMarketWorker, signal_store: SignalStore) -> APIRouter:
    router = APIRouter()

    @router.get("/api/v1/signal")
    async def get_signal() -> dict[str, Any]:
        if worker.last_signal is None:
            return {"status": "warmup", "signal": "HOLD", "confidence": 0.0}

        return {
            "status": "ready",
            "signal": worker.last_signal.signal,
            "confidence": worker.last_signal.confidence,
            "symbol": worker.last_signal.symbol,
        }

    @router.post("/api/v1/signal/ingest")
    async def ingest_signal(tick: TickEvent) -> dict[str, Any]:
        signal = await worker.ingest_tick(tick)
        return {
            "status": "accepted",
            "signal": signal.signal,
            "confidence": signal.confidence,
            "symbol": signal.symbol,
            "strategy_id": signal.strategy_id,
        }

    @router.get("/api/v1/signals/recent")
    async def recent_signals(
        limit: int = Query(
            default=settings.signal_history_limit_default,
            ge=1,
            le=settings.signal_history_limit_max,
        ),
        source: str = Query(default="auto", pattern="^(auto|supabase|firestore)$"),
    ) -> dict[str, Any]:
        selected_source: Literal["auto", "supabase", "firestore"] = "auto"
        if source == "supabase":
            selected_source = "supabase"
        elif source == "firestore":
            selected_source = "firestore"

        used_source, records = await signal_store.list_recent(
            limit=limit,
            source=selected_source,
        )
        return {
            "source": used_source,
            "count": len(records),
            "signals": [item.model_dump() for item in records],
        }

    return router
