import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from time import monotonic

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    build_inference_router,
    build_matching_router,
    build_optimize_router,
    build_signal_router,
    build_strategy_orchestration_router,
    build_summary_router,
    build_system_router,
)
from app.config import settings
from app.http import register_error_handlers, register_request_id_middleware
from app.runtime_container import build_runtime_container
from app.settings_validation import validate_runtime_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)

SERVICE_STARTED_AT = monotonic()
validate_runtime_settings()
runtime = build_runtime_container(started_at=SERVICE_STARTED_AT)
worker = runtime.worker
signal_store = runtime.signal_store
signal_service = runtime.signal_service
inference_service = runtime.inference_service
optimization_service = runtime.optimization_service
strategy_orchestration_service = runtime.strategy_orchestration_service
summary_service = runtime.summary_service
matching_service = runtime.matching_service
system_status_service = runtime.system_status_service


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    await worker.start()
    await signal_service.startup()
    await inference_service.startup()
    try:
        yield
    finally:
        await inference_service.shutdown()
        await signal_service.shutdown()
        await worker.stop()
        await signal_store.aclose()


def _build_cors_origins() -> list[str]:
    if settings.cors_allow_origins.strip() == "*":
        return ["*"]
    values = [s.strip() for s in settings.cors_allow_origins.split(",") if s.strip()]
    return values or ["*"]


app = FastAPI(
    title="Cerberus Strategy Service",
    version=settings.service_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_build_cors_origins(),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_request_id_middleware(app)
register_error_handlers(app, logger)

app.include_router(build_system_router(system_status_service))
app.include_router(build_signal_router(signal_service))
app.include_router(build_inference_router(inference_service))
app.include_router(build_strategy_orchestration_router(strategy_orchestration_service))
app.include_router(build_summary_router(summary_service))
app.include_router(build_optimize_router(optimization_service))
app.include_router(build_matching_router(matching_service))
