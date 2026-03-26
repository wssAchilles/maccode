from __future__ import annotations

from typing import TYPE_CHECKING

from app.config import settings
from app.market_ingest_runtime.stream_io import refresh_market_stream_backlog_metrics
from app.market_ingest_runtime.stream_reclaim import reclaim_market_stream_entries
from app.market_ingest_runtime.time_utils import current_epoch_millis

if TYPE_CHECKING:
    from app.redis_worker import RedisMarketWorker


def should_run_market_stream_maintenance(last_maintenance_at_ms: int) -> bool:
    interval_ms = max(settings.market_stream_reclaim_interval_ms, 0)
    if interval_ms == 0:
        return False
    if last_maintenance_at_ms <= 0:
        return True
    return current_epoch_millis() - last_maintenance_at_ms >= interval_ms


async def run_market_stream_maintenance(
    worker: RedisMarketWorker,
    stream_key: str,
    group: str,
    consumer: str,
) -> None:
    await refresh_market_stream_backlog_metrics(worker, stream_key, group)
    if not settings.market_stream_reclaim_enabled:
        return
    await reclaim_market_stream_entries(worker, stream_key, group, consumer)


__all__ = [
    "run_market_stream_maintenance",
    "should_run_market_stream_maintenance",
]
