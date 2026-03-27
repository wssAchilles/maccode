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
    redis = worker.redis_client
    assert redis is not None
    pending_raw = await redis.xpending(stream_key, group)
    pending = extract_market_pending_count(pending_raw)

    groups_raw = await redis.xinfo_groups(stream_key)
    lag = extract_market_lag(groups_raw, group)
    worker.update_market_stream_backlog(pending=pending, lag=lag)
