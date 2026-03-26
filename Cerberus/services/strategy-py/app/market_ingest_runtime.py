from __future__ import annotations

import asyncio
import json
import logging
import socket
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

import grpc
from redis.exceptions import RedisError

from app.config import settings
from app.market_payloads import market_channels_from_settings, parse_tick_payload

if TYPE_CHECKING:
    from app.redis_worker import RedisMarketWorker
    from app.schemas import TickEvent

logger = logging.getLogger(__name__)


async def run_market_loop(worker: RedisMarketWorker) -> None:
    assert worker._redis is not None
    if settings.market_stream_enabled:
        try:
            await run_market_stream_loop(worker)
            return
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            worker.last_error = f"market stream: {exc}"
            worker.market_stream_fallbacks += 1
            logger.warning("market stream loop failed, fallback to pubsub: %s", exc)
            if not settings.market_stream_legacy_pubsub_fallback:
                raise

    await run_market_pubsub_loop(worker)


async def run_market_pubsub_loop(worker: RedisMarketWorker) -> None:
    assert worker._redis is not None
    pubsub = worker._redis.pubsub()
    channels = market_channels_from_settings(settings.market_channels, settings.market_channel)
    await pubsub.subscribe(*channels)
    worker.market_ingest_mode = "pubsub"
    logger.info("subscribed to market pubsub channels: %s", ", ".join(channels))

    consecutive_retriable_failures = 0
    try:
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if not message:
                await asyncio.sleep(0.05)
                continue

            tick = parse_tick_message(message)
            if tick is None:
                continue

            try:
                await worker.ingest_tick(tick)
                consecutive_retriable_failures = 0
            except Exception as exc:  # noqa: BLE001
                worker.last_error = str(exc)
                if is_retriable_error(exc):
                    consecutive_retriable_failures += 1
                    backoff_seconds = compute_backoff_seconds(consecutive_retriable_failures)
                    logger.warning(
                        "tick ingest retriable failure (attempt=%s, backoff=%.2fs): %s",
                        consecutive_retriable_failures,
                        backoff_seconds,
                        exc,
                    )
                    await asyncio.sleep(backoff_seconds)
                else:
                    consecutive_retriable_failures = 0
                    logger.warning("tick ingest non-retriable failure: %s", exc)
    finally:
        await pubsub.unsubscribe(*channels)
        await pubsub.aclose()  # type: ignore[no-untyped-call]


async def run_market_stream_loop(worker: RedisMarketWorker) -> None:
    assert worker._redis is not None
    stream_key = settings.market_stream_key.strip() or "cerberus.market.events"
    group = settings.market_stream_consumer_group.strip() or "strategy-market"
    consumer = market_stream_consumer_name()

    await ensure_market_stream_group(worker, stream_key, group, consumer)
    worker.market_ingest_mode = "stream"
    logger.info(
        "consuming market stream=%s group=%s consumer=%s",
        stream_key,
        group,
        consumer,
    )
    await replay_pending_market_stream_entries(worker, stream_key, group, consumer)
    await market_stream_consume_loop(worker, stream_key, group, consumer)


async def ensure_market_stream_group(
    worker: RedisMarketWorker,
    stream_key: str,
    group: str,
    consumer: str,
) -> None:
    assert worker._redis is not None
    try:
        await worker._redis.xgroup_create(stream_key, group, id="0", mkstream=True)
    except RedisError as exc:
        if "BUSYGROUP" not in str(exc):
            raise
    try:
        await worker._redis.xgroup_createconsumer(stream_key, group, consumer)
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


async def market_stream_consume_loop(
    worker: RedisMarketWorker,
    stream_key: str,
    group: str,
    consumer: str,
) -> None:
    consecutive_failures = 0
    max_retries = max(settings.market_stream_max_retries_before_fallback, 0)
    last_maintenance_at_ms = 0
    while True:
        try:
            if should_run_market_stream_maintenance(last_maintenance_at_ms):
                try:
                    await run_market_stream_maintenance(worker, stream_key, group, consumer)
                except Exception as exc:  # noqa: BLE001
                    worker.market_stream_reclaim_failures += 1
                    worker.last_error = f"market stream maintenance: {exc}"
                    logger.warning("market stream maintenance failed: %s", exc)
                last_maintenance_at_ms = current_epoch_millis()
            entries = await read_market_stream_entries(
                worker,
                stream_key=stream_key,
                group=group,
                consumer=consumer,
                stream_id=">",
                count=max(settings.market_stream_read_batch_size, 1),
                block_ms=max(settings.market_stream_read_block_ms, 1),
            )
            if entries:
                await process_market_stream_batch(worker, stream_key, group, entries)
                if settings.market_stream_batch_window_ms > 0:
                    await asyncio.sleep(settings.market_stream_batch_window_ms / 1_000.0)
            consecutive_failures = 0
            worker.market_stream_consecutive_failures = 0
            worker.last_market_stream_retry_backoff_ms = None
            continue
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            consecutive_failures += 1
            worker.market_stream_retry_attempts += 1
            worker.market_stream_consecutive_failures = consecutive_failures
            worker.last_error = f"market stream: {exc}"
            backoff_ms = compute_market_stream_backoff_ms(consecutive_failures)
            worker.last_market_stream_retry_backoff_ms = backoff_ms
            logger.warning(
                "market stream retrying after failure (attempt=%s/%s, backoff_ms=%s): %s",
                consecutive_failures,
                max_retries,
                backoff_ms,
                exc,
            )
            if consecutive_failures > max_retries:
                raise
            await asyncio.sleep(backoff_ms / 1_000.0)


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


async def reclaim_market_stream_entries(
    worker: RedisMarketWorker,
    stream_key: str,
    group: str,
    consumer: str,
) -> None:
    assert worker._redis is not None
    worker.market_stream_reclaim_attempts += 1
    worker.last_market_stream_reclaim_at_ms = current_epoch_millis()

    claim_raw = await worker._redis.xautoclaim(
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

    worker.market_stream_reclaimed += len(reclaimed)
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
    assert worker._redis is not None

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
    await worker._redis.xadd(
        market_stream_poison_stream_key(),
        {"data": data},
        maxlen=max(settings.market_stream_poison_stream_maxlen, 1),
        approximate=True,
    )
    worker.market_stream_poisoned += 1
    worker.last_market_stream_poison_id = stream_id


def market_stream_poison_stream_key() -> str:
    return settings.market_stream_poison_stream_key.strip() or "cerberus.market.events.poison"


def current_epoch_millis() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1_000)


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


async def process_market_stream_batch(
    worker: RedisMarketWorker,
    stream_key: str,
    group: str,
    entries: list[tuple[str, dict[str, Any]]],
) -> None:
    ack_ids: list[str] = []
    for stream_id, fields in entries:
        raw_payload, channel = parse_market_stream_entry(fields)
        if raw_payload is None:
            ack_ids.append(stream_id)
            continue

        tick = parse_tick_payload(raw_payload, channel)
        if tick is None:
            ack_ids.append(stream_id)
            continue

        try:
            await worker.ingest_tick(tick)
            ack_ids.append(stream_id)
            worker.market_stream_events += 1
            worker.last_market_stream_id = stream_id
        except Exception as exc:  # noqa: BLE001
            worker.last_error = str(exc)
            if is_retriable_error(exc):
                if ack_ids:
                    await ack_market_stream_entries(worker, stream_key, group, ack_ids)
                raise
            logger.warning("market stream non-retriable ingest failure: %s", exc)
            ack_ids.append(stream_id)

    if ack_ids:
        await ack_market_stream_entries(worker, stream_key, group, ack_ids)


def parse_market_stream_entry(fields: dict[str, Any]) -> tuple[str | None, str | None]:
    raw = fields.get("data") or fields.get("payload") or fields.get("json")
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="ignore")
    if not isinstance(raw, str) or not raw.strip():
        return None, None

    channel = fields.get("channel")
    if isinstance(channel, bytes):
        channel = channel.decode("utf-8", errors="ignore")
    if not isinstance(channel, str):
        channel = None

    return raw, channel


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


def market_stream_consumer_name() -> str:
    configured = settings.market_stream_consumer_name.strip()
    if configured:
        return configured
    host = socket.gethostname().strip() or "local"
    return f"strategy-{host}"


def compute_market_stream_backoff_ms(attempt: int) -> int:
    base = max(settings.market_stream_retry_backoff_ms, 1)
    maximum = max(settings.market_stream_retry_backoff_max_ms, base)
    value = base * (2 ** max(attempt - 1, 0))
    return min(value, maximum)


def parse_tick_message(message: dict[str, object]) -> TickEvent | None:
    raw = message.get("data")
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="ignore")
    if not isinstance(raw, str):
        return None
    channel = message.get("channel")
    if isinstance(channel, bytes):
        channel = channel.decode("utf-8", errors="ignore")
    return parse_tick_payload(raw, str(channel) if isinstance(channel, str) else None)


def is_retriable_error(exc: Exception) -> bool:
    if isinstance(exc, (asyncio.TimeoutError, ConnectionError, RedisError)):
        return True
    if isinstance(exc, grpc.aio.AioRpcError):
        return exc.code() in {
            grpc.StatusCode.UNAVAILABLE,
            grpc.StatusCode.DEADLINE_EXCEEDED,
            grpc.StatusCode.RESOURCE_EXHAUSTED,
            grpc.StatusCode.ABORTED,
        }
    return False


def compute_backoff_seconds(attempt: int) -> float:
    base = max(settings.retriable_base_backoff_seconds, 0.01)
    maximum = max(settings.retriable_max_backoff_seconds, base)
    value = base * (2 ** max(attempt - 1, 0))
    return min(value, maximum)
