from __future__ import annotations

from typing import TYPE_CHECKING

from .parsing import extract_market_lag, extract_market_pending_count

if TYPE_CHECKING:
    from app.redis_worker import RedisMarketWorker


async def refresh_market_stream_backlog_metrics(
    worker: RedisMarketWorker,
    stream_key: str,
    group: str,
) -> None:
    assert worker._redis is not None
    pending_raw = await worker._redis.xpending(stream_key, group)
    worker.market_stream_pending = extract_market_pending_count(pending_raw)

    groups_raw = await worker._redis.xinfo_groups(stream_key)
    worker.market_stream_lag = extract_market_lag(groups_raw, group)
