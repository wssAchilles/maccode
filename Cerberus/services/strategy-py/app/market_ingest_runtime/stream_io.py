from __future__ import annotations

from typing import TYPE_CHECKING, Any

from redis.exceptions import RedisError

from .time_utils import current_epoch_millis

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


def flatten_stream_entries(raw: Any) -> list[tuple[str, dict[str, Any]]]:
    entries: list[tuple[str, dict[str, Any]]] = []
    if not isinstance(raw, list):
        return entries
    for stream_bucket in raw:
        if not isinstance(stream_bucket, (list, tuple)) or len(stream_bucket) != 2:
            continue
        bucket_entries = stream_bucket[1]
        if not isinstance(bucket_entries, list):
            continue
        for item in bucket_entries:
            if not isinstance(item, (list, tuple)) or len(item) != 2:
                continue
            stream_id, fields = item
            if not isinstance(stream_id, str) or not isinstance(fields, dict):
                continue
            entries.append((stream_id, fields))
    return entries


def flatten_claimed_entries(raw: Any) -> list[tuple[str, dict[str, Any]]]:
    if isinstance(raw, (list, tuple)) and len(raw) >= 2:
        claimed = raw[1]
    else:
        claimed = []

    entries: list[tuple[str, dict[str, Any]]] = []
    if not isinstance(claimed, list):
        return entries

    for item in claimed:
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            continue
        stream_id, fields = item
        if isinstance(stream_id, bytes):
            stream_id = stream_id.decode("utf-8", errors="ignore")
        if not isinstance(stream_id, str) or not isinstance(fields, dict):
            continue
        entries.append((stream_id, normalize_stream_fields(fields)))
    return entries


def normalize_stream_fields(fields: dict[Any, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key, value in fields.items():
        if isinstance(key, bytes):
            normalized_key = key.decode("utf-8", errors="ignore")
        else:
            normalized_key = str(key)
        normalized[normalized_key] = value
    return normalized


def parse_pending_range_entry(item: Any) -> dict[str, int]:
    if not isinstance(item, dict):
        return {"times_delivered": 1}
    times_delivered = item.get("times_delivered")
    if times_delivered is None:
        times_delivered = item.get(b"times_delivered")
    if times_delivered is None:
        times_delivered = 1
    if isinstance(times_delivered, int):
        return {"times_delivered": times_delivered}
    if isinstance(times_delivered, str) and times_delivered.isdigit():
        return {"times_delivered": int(times_delivered)}
    if isinstance(times_delivered, bytes):
        decoded = times_delivered.decode("utf-8", errors="ignore")
        if decoded.isdigit():
            return {"times_delivered": int(decoded)}
    return {"times_delivered": 1}


def extract_market_pending_count(raw: Any) -> int:
    if isinstance(raw, dict):
        value = raw.get("pending", 0)
        if isinstance(value, int):
            return max(value, 0)
        if isinstance(value, str) and value.isdigit():
            return int(value)
        return 0
    if isinstance(raw, (list, tuple)) and raw:
        first = raw[0]
        if isinstance(first, int):
            return max(first, 0)
        if isinstance(first, str) and first.isdigit():
            return int(first)
    return 0


def extract_market_lag(raw: Any, group: str) -> int:
    if not isinstance(raw, list):
        return 0

    target = group.strip()
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        if isinstance(name, bytes):
            name = name.decode("utf-8", errors="ignore")
        if not isinstance(name, str) or name.strip() != target:
            continue

        lag_value = item.get("lag", 0)
        if isinstance(lag_value, int):
            return max(lag_value, 0)
        if isinstance(lag_value, str) and lag_value.isdigit():
            return int(lag_value)
        return 0

    return 0


__all__ = [
    "ack_market_stream_entries",
    "current_epoch_millis",
    "extract_market_lag",
    "extract_market_pending_count",
    "flatten_claimed_entries",
    "flatten_stream_entries",
    "normalize_stream_fields",
    "parse_pending_range_entry",
    "pending_delivery_count",
    "read_market_stream_entries",
    "refresh_market_stream_backlog_metrics",
]
