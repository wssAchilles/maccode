from __future__ import annotations

from typing import Any

from application.services.stats_service import StatsService
from fastapi import APIRouter, Query, Request
from shared.schemas.common import ResponseWrapper

router = APIRouter(tags=["stats"])


@router.get("/stats/realtime", response_model=ResponseWrapper[dict[str, Any]])
def get_realtime_stats(request: Request) -> ResponseWrapper[dict[str, Any]]:
    return ResponseWrapper.success_response(
        StatsService(request.app.state.runtime).get_realtime_report()
    )


@router.get("/stats/history", response_model=ResponseWrapper[list[dict[str, Any]]])
def get_history_stats(
    request: Request,
    limit: int = Query(default=100, ge=1, le=5000),
) -> ResponseWrapper[list[dict[str, Any]]]:
    return ResponseWrapper.success_response(
        StatsService(request.app.state.runtime).get_history(limit)
    )


@router.get("/stats/cumulative", response_model=ResponseWrapper[dict[str, Any]])
def get_cumulative_stats(request: Request) -> ResponseWrapper[dict[str, Any]]:
    return ResponseWrapper.success_response(
        StatsService(request.app.state.runtime).get_cumulative_stats()
    )
