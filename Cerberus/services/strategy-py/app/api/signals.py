from typing import Any

from fastapi import APIRouter, Query

from app.config import settings
from app.schemas import TickEvent
from app.signal_service import SignalService


def build_signal_router(service: SignalService) -> APIRouter:
    router = APIRouter()

    @router.get("/api/v1/signal")
    async def get_signal() -> dict[str, Any]:
        return service.current_signal()

    @router.post("/api/v1/signal/ingest")
    async def ingest_signal(tick: TickEvent) -> dict[str, Any]:
        return await service.ingest_tick(tick)

    @router.get("/api/v1/signals/recent")
    async def recent_signals(
        limit: int = Query(
            default=settings.signal_history_limit_default,
            ge=1,
            le=settings.signal_history_limit_max,
        ),
        source: str = Query(default="auto", pattern="^(auto|supabase|firestore)$"),
    ) -> dict[str, Any]:
        return await service.recent_signals(limit=limit, source=source)

    return router
