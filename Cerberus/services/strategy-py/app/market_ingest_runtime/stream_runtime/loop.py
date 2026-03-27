from __future__ import annotations

import logging
import socket
from typing import TYPE_CHECKING

from app.config import settings

from .consume import market_stream_consume_loop
from .group import ensure_market_stream_group, replay_pending_market_stream_entries

if TYPE_CHECKING:
    from app.redis_worker import RedisMarketWorker

logger = logging.getLogger(__name__)


async def run_market_stream_loop(worker: RedisMarketWorker) -> None:
    assert worker.redis_client is not None
    stream_key = settings.market_stream_key.strip() or "cerberus.market.events"
    group = settings.market_stream_consumer_group.strip() or "strategy-market"
    consumer = market_stream_consumer_name()

    await ensure_market_stream_group(worker, stream_key, group, consumer)
    worker.set_market_ingest_mode("stream")
    logger.info(
        "consuming market stream=%s group=%s consumer=%s",
        stream_key,
        group,
        consumer,
    )
    await replay_pending_market_stream_entries(worker, stream_key, group, consumer)
    await market_stream_consume_loop(worker, stream_key, group, consumer)


def market_stream_consumer_name() -> str:
    configured = settings.market_stream_consumer_name.strip()
    if configured:
        return configured
    host = socket.gethostname().strip() or "local"
    return f"strategy-{host}"


__all__ = ["market_stream_consumer_name", "run_market_stream_loop"]
