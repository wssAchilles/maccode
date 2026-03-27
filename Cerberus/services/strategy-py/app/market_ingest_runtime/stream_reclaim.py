from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from app.config import settings

from .stream_io import (
    ack_market_stream_entries,
    flatten_claimed_entries,
    pending_delivery_count,
)
from .stream_processing import process_market_stream_batch
from .time_utils import current_epoch_millis

if TYPE_CHECKING:
    from app.redis_worker import RedisMarketWorker

logger = logging.getLogger(__name__)


async def reclaim_market_stream_entries(
    worker: RedisMarketWorker,
    stream_key: str,
    group: str,
    consumer: str,
) -> None:
    redis = worker.redis_client
    assert redis is not None
    worker.mark_market_stream_reclaim_attempt(current_epoch_millis())

    claim_raw = await redis.xautoclaim(
        stream_key,
        group,
        consumer,
        min_idle_time=max(settings.market_stream_reclaim_idle_ms, 1),
        start_id="0-0",
        count=max(settings.market_stream_reclaim_batch_size, 1),
    )
    reclaimed = flatten_claimed_entries(claim_raw)
    if not reclaimed:
        return

    worker.mark_market_stream_reclaimed(len(reclaimed))
    logger.info("reclaimed %s stuck market stream entries", len(reclaimed))

    processable: list[tuple[str, dict[str, Any]]] = []
    ack_ids: list[str] = []
    for stream_id, fields in reclaimed:
        deliveries = await pending_delivery_count(worker, stream_key, group, stream_id)
        max_delivery_attempts = max(settings.market_stream_max_delivery_attempts, 0)
        if deliveries > max_delivery_attempts > 0:
            await poison_market_stream_entry(
                worker,
                stream_key=stream_key,
                group=group,
                consumer=consumer,
                stream_id=stream_id,
                fields=fields,
                deliveries=deliveries,
            )
            ack_ids.append(stream_id)
            continue
        processable.append((stream_id, fields))

    if processable:
        await process_market_stream_batch(worker, stream_key, group, processable)
    if ack_ids:
        await ack_market_stream_entries(worker, stream_key, group, ack_ids)


async def poison_market_stream_entry(
    worker: RedisMarketWorker,
    *,
    stream_key: str,
    group: str,
    consumer: str,
    stream_id: str,
    fields: dict[str, Any],
    deliveries: int,
) -> None:
    redis = worker.redis_client
    assert redis is not None

    payload = {
        "stream": stream_key,
        "group": group,
        "consumer": consumer,
        "stream_id": stream_id,
        "deliveries": deliveries,
        "reason": "max_delivery_attempts_exceeded",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "schema_version": settings.event_schema_version,
        "fields": fields,
    }
    data = json.dumps(payload, separators=(",", ":"))
    await redis.xadd(
        market_stream_poison_stream_key(),
        {"data": data},
        maxlen=max(settings.market_stream_poison_stream_maxlen, 1),
        approximate=True,
    )
    worker.mark_market_stream_poisoned(stream_id)


def market_stream_poison_stream_key() -> str:
    return settings.market_stream_poison_stream_key.strip() or "cerberus.market.events.poison"


__all__ = [
    "market_stream_poison_stream_key",
    "poison_market_stream_entry",
    "reclaim_market_stream_entries",
]
