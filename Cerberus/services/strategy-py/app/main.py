import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from time import monotonic

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    build_matching_router,
    build_optimize_router,
    build_signal_router,
    build_system_router,
)
from app.config import settings
from app.http import register_error_handlers, register_request_id_middleware
from app.redis_worker import RedisMarketWorker
from app.signal_store import SignalStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)

SERVICE_STARTED_AT = monotonic()
worker = RedisMarketWorker()
signal_store = SignalStore()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    await worker.start()
    try:
        yield
    finally:
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

app.include_router(build_system_router(worker, signal_store, SERVICE_STARTED_AT))
app.include_router(build_signal_router(worker, signal_store))
app.include_router(build_optimize_router())
app.include_router(build_matching_router(worker))
