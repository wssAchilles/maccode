from __future__ import annotations

from typing import Any

from app.matching_observability import collect_matching_snapshot
from app.redis_worker import RedisMarketWorker
from app.signal_store import SignalStore

from .worker_state import build_worker_state


async def build_persistence_status(
    worker: RedisMarketWorker,
    signal_store: SignalStore,
    *,
    request_id: str,
) -> dict[str, Any]:
    matching_snapshot = await collect_matching_snapshot(worker, request_id=request_id)
    idempotency = worker.idempotency_snapshot()

    return {
        "status": "ok",
        "worker": {
            "processed_ticks": worker.processed_ticks,
            "forwarded_executions": worker.forwarded_executions,
            "last_execution_id": worker.last_execution_id,
            "last_tick_at": worker.last_tick_at,
            "last_error": worker.last_error,
            "has_last_signal": worker.last_signal is not None,
            "tracked_symbols": worker.tracked_symbols,
            "idempotency": idempotency,
            **build_worker_state(worker),
        },
        "matching": {
            "health": matching_snapshot.health,
            "stats": matching_snapshot.stats,
        },
        "stores": signal_store.status(),
    }
