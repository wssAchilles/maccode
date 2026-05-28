from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from application.services.stats_service import StatsService
from shared.schemas.common import ResponseWrapper

router = APIRouter(tags=["stats"])


@router.get("/stats/realtime", response_model=ResponseWrapper[dict[str, Any]])
def get_realtime_stats() -> ResponseWrapper[dict[str, Any]]:
    return ResponseWrapper.success_response(StatsService().get_realtime_report())
