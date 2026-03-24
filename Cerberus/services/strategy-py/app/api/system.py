from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response

from app.config import settings
from app.http import PROMETHEUS_CONTENT_TYPE, request_id_from
from app.redis_worker import RedisMarketWorker
from app.signal_store import SignalStore
from app.api.system_helpers import (
    build_metrics_lines,
    build_persistence_status,
    build_ready_content,
)


def build_system_router(
    worker: RedisMarketWorker, signal_store: SignalStore, started_at: float
) -> APIRouter:
    router = APIRouter()

    @router.get("/health")
    async def health() -> dict[str, str]:
        return {
            "status": "ok",
            "service": settings.service_name,
            "version": settings.service_version,
        }

    @router.get("/ready")
    async def ready(request: Request) -> JSONResponse:
        status_code, content = await build_ready_content(
            worker,
            started_at=started_at,
            request_id=request_id_from(request),
        )
        return JSONResponse(status_code=status_code, content=content)

    @router.get("/metrics")
    async def metrics(request: Request) -> Response:
        lines = await build_metrics_lines(
            worker,
            signal_store,
            started_at=started_at,
            request_id=request_id_from(request),
        )
        return Response(content="\n".join(lines) + "\n", media_type=PROMETHEUS_CONTENT_TYPE)

    @router.get("/api/v1/status/persistence")
    async def persistence_status(request: Request) -> dict[str, Any]:
        return await build_persistence_status(
            worker,
            signal_store,
            request_id=request_id_from(request),
        )

    return router
