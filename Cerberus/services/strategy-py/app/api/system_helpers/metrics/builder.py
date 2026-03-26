from __future__ import annotations

from time import monotonic

from app.redis_worker import RedisMarketWorker
from app.signal_store import SignalStore

from .context import build_matching_metrics_context
from .line_builders import (
    base_metrics_lines,
    idempotency_metrics_lines,
    market_stream_metrics_lines,
    matching_metrics_lines,
    stores_metrics_lines,
    worker_runtime_metrics_lines,
)


async def build_metrics_lines(
    worker: RedisMarketWorker,
    signal_store: SignalStore,
    *,
    started_at: float,
    request_id: str,
) -> list[str]:
    uptime_seconds = int(max(monotonic() - started_at, 0.0))
    idempotency = worker.idempotency_snapshot()
    stores = signal_store.status()
    matching = await build_matching_metrics_context(worker, request_id=request_id)

    lines: list[str] = []
    lines.extend(base_metrics_lines(uptime_seconds))
    lines.extend(worker_runtime_metrics_lines(worker))
    lines.extend(market_stream_metrics_lines(worker))
    lines.extend(stores_metrics_lines(stores))
    lines.extend(matching_metrics_lines(worker, matching))
    lines.extend(idempotency_metrics_lines(idempotency))
    return lines


__all__ = ["build_metrics_lines"]
