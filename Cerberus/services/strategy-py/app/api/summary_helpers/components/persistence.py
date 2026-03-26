from __future__ import annotations

from app.api.system_helpers import build_persistence_status
from app.redis_worker import RedisMarketWorker
from app.signal_store import SignalStore

from .response import component_error, component_ok


async def build_persistence_component(
    worker: RedisMarketWorker,
    signal_store: SignalStore,
    *,
    request_id: str,
) -> dict[str, object]:
    try:
        payload = await build_persistence_status(worker, signal_store, request_id=request_id)
    except Exception as exc:
        return component_error(
            code="summary_persistence_failed",
            message=f"persistence status unavailable: {exc}",
            request_id=request_id,
            status_code=502,
        )
    return component_ok(payload)
