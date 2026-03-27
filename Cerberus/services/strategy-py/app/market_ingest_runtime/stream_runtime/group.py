from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from redis.exceptions import RedisError

from app.config import settings
from app.market_ingest_runtime.stream_io import read_market_stream_entries
from app.market_ingest_runtime.stream_processing import process_market_stream_batch

if TYPE_CHECKING:
    from app.redis_worker import RedisMarketWorker

logger = logging.getLogger(__name__)


async def ensure_market_stream_group(
    worker: RedisMarketWorker,
    stream_key: str,
    group: str,
    consumer: str,
) -> None:
    redis = worker.redis_client
    assert redis is not None
    try:
        await redis.xgroup_create(stream_key, group, id="0", mkstream=True)
    except RedisError as exc:
        if "BUSYGROUP" not in str(exc):
            raise
    try:
        await redis.xgroup_createconsumer(stream_key, group, consumer)
    except RedisError:
        pass


async def replay_pending_market_stream_entries(
    worker: RedisMarketWorker,
    stream_key: str,
    group: str,
    consumer: str,
) -> None:
    pending = await read_market_stream_entries(
        worker,
        stream_key=stream_key,
        group=group,
        consumer=consumer,
        stream_id="0",
        count=max(settings.market_stream_pending_replay_count, 1),
        block_ms=10,
    )
    if not pending:
        return
    logger.info("replaying %s pending market stream entries", len(pending))
    await process_market_stream_batch(worker, stream_key, group, pending)


__all__ = ["ensure_market_stream_group", "replay_pending_market_stream_entries"]
