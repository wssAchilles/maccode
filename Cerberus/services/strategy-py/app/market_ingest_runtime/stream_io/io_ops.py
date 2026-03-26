from __future__ import annotations

from typing import TYPE_CHECKING, Any

from redis.exceptions import RedisError

from .parsing import flatten_stream_entries, parse_pending_range_entry

if TYPE_CHECKING:
    from app.redis_worker import RedisMarketWorker


async def read_market_stream_entries(
    worker: RedisMarketWorker,
    *,
    stream_key: str,
    group: str,
    consumer: str,
    stream_id: str,
    count: int,
    block_ms: int,
) -> list[tuple[str, dict[str, Any]]]:
    assert worker._redis is not None
    try:
        raw = await worker._redis.xreadgroup(
            groupname=group,
            consumername=consumer,
            streams={stream_key: stream_id},
            count=count,
            block=block_ms,
        )
    except RedisError as exc:
        worker.market_stream_read_failures += 1
        raise RuntimeError(f"xreadgroup failed: {exc}") from exc
    return flatten_stream_entries(raw)


async def ack_market_stream_entries(
    worker: RedisMarketWorker,
    stream_key: str,
    group: str,
    ids: list[str],
) -> None:
    assert worker._redis is not None
    if not ids:
        return
    try:
        await worker._redis.xack(stream_key, group, *ids)
    except RedisError as exc:
        worker.market_stream_ack_failures += 1
        raise RuntimeError(f"xack failed: {exc}") from exc


async def pending_delivery_count(
    worker: RedisMarketWorker,
    stream_key: str,
    group: str,
    stream_id: str,
) -> int:
    assert worker._redis is not None
    pending_raw = await worker._redis.xpending_range(
        stream_key,
        group,
        min=stream_id,
        max=stream_id,
        count=1,
    )
    if not pending_raw:
        return 1
    parsed = parse_pending_range_entry(pending_raw[0])
    return max(parsed.get("times_delivered", 1), 1)
