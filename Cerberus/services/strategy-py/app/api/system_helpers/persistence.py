from __future__ import annotations

from typing import Any

from app.ports import MatchingObservabilityPort, RuntimeStatusPort, StoreStatusPort

from .worker_state import build_worker_state


async def build_persistence_status(
    runtime_status: RuntimeStatusPort,
    signal_store_status: StoreStatusPort,
    matching_observability: MatchingObservabilityPort,
    *,
    request_id: str,
) -> dict[str, Any]:
    snapshot = runtime_status.runtime_snapshot()
    matching_snapshot = await matching_observability.collect_snapshot(request_id=request_id)
    idempotency = runtime_status.idempotency_snapshot()

    return {
        "status": "ok",
        "worker": {
            "processed_ticks": snapshot.processed_ticks,
            "forwarded_executions": snapshot.forwarded_executions,
            "last_execution_id": snapshot.last_execution_id,
            "last_tick_at": snapshot.last_tick_at,
            "last_error": snapshot.last_error,
            "has_last_signal": snapshot.last_signal is not None,
            "tracked_symbols": list(snapshot.tracked_symbols),
            "idempotency": idempotency,
            **build_worker_state(runtime_status),
        },
        "matching": {
            "health": matching_snapshot.health,
            "stats": matching_snapshot.stats,
        },
        "stores": signal_store_status.status(),
    }
