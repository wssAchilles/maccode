from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query, Request

from app.config import settings
from app.http import request_id_from
from app.summary_service import StrategySummaryService


def build_summary_router(service: StrategySummaryService) -> APIRouter:
    router = APIRouter()

    @router.get("/api/v1/summary")
    async def strategy_summary(
        request: Request,
        symbol: str = Query(default="BTCUSDT", min_length=1, max_length=24),
        recent_limit: int = Query(
            default=8,
            ge=1,
            le=settings.signal_history_limit_max,
        ),
        source: str = Query(default="auto", pattern="^(auto|supabase|firestore)$"),
        orderbook_depth: int = Query(default=10, ge=1, le=200),
    ) -> dict[str, Any]:
        return await service.summary(
            symbol=symbol,
            recent_limit=recent_limit,
            source=source,
            orderbook_depth=orderbook_depth,
            request_id=request_id_from(request),
        )

    return router
