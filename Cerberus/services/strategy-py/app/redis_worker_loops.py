from __future__ import annotations

import asyncio
import json
import logging
import socket
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from uuid import uuid4

import grpc
from redis.exceptions import RedisError

from app.config import settings
from app.execution_event_payloads import (
    build_matching_execution_payload,
    build_matching_submission_payload,
)
from app.execution_relay import filter_new_executions
from app.market_payloads import market_channels_from_settings, parse_tick_payload

if TYPE_CHECKING:
    from app.redis_worker import RedisMarketWorker
    from app.schemas import Signal, TickEvent

logger = logging.getLogger(__name__)


async def run_market_loop(worker: RedisMarketWorker) -> None:
    assert worker._redis is not None
    if settings.market_stream_enabled:
        try:
            await run_market_stream_loop(worker)
            return
        except asyncio.CancelledError:
            raise
        except Exception as exc:
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
            except Exception as exc:
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
        # Consumer can already exist in a long-lived deployment.
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
    while True:
        try:
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
        except Exception as exc:
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
        except Exception as exc:
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


def parse_tick_message(message: dict[str, object]) -> TickEvent | None:
    raw = message.get("data")
    if not isinstance(raw, str):
        return None
    channel = message.get("channel")
    return parse_tick_payload(raw, str(channel) if isinstance(channel, str) else None)


async def publish_signal_event(
    worker: RedisMarketWorker,
    signal: Signal,
    tick: TickEvent,
    signal_id: str,
) -> None:
    payload = {
        "strategy_id": signal.strategy_id,
        "symbol": signal.symbol,
        "signal": signal.signal,
        "confidence": signal.confidence,
        "price": tick.price,
        "quantity": tick.quantity,
        "event_time": tick.event_time,
        "signal_id": signal_id,
    }
    await publish_event(
        worker=worker,
        channel=settings.signal_channel,
        event_type="strategy.signal.generated",
        payload=payload,
        correlation_id=signal_id,
    )


async def publish_matching_submission(
    worker: RedisMarketWorker, signal: Signal, tick_price: float, signal_id: str
) -> None:
    if worker._redis is None:
        return

    claimed_order_id: str | None = None
    try:
        order_event = await worker._matching.submit_from_signal(
            signal, tick_price, idempotency_key=signal_id
        )
        if order_event is None:
            return
        order_id = str(order_event.get("order_id", "")).strip()
        if order_id:
            if not await worker.claim_order(order_id):
                return
            claimed_order_id = order_id
        channel = f"{settings.trade_execution_channel_prefix}.{settings.strategy_account_id}"
        payload = build_matching_submission_payload(
            strategy_id=signal.strategy_id,
            account_id=settings.strategy_account_id,
            order_event=order_event,
        )
        payload["signal_id"] = signal_id
        await publish_event(
            worker=worker,
            channel=channel,
            event_type="matching.order.submitted",
            payload=payload,
            correlation_id=signal_id,
        )
    except Exception as exc:
        if claimed_order_id:
            await worker.release_order_claim(claimed_order_id)
        logger.warning("matching submit flow failed: %s", exc)


async def run_execution_relay_loop(worker: RedisMarketWorker) -> None:
    if not worker._matching.enabled or worker._redis is None:
        return

    channel = f"{settings.trade_execution_channel_prefix}.{settings.strategy_account_id}"
    while True:
        try:
            items = await worker._matching.list_recent_executions(
                account_id=settings.strategy_account_id,
                limit=max(settings.execution_relay_batch_limit, 1),
            )
            publish_batch: list[PublishedEvent] = []
            claimed_order_ids: list[str] = []
            next_last_execution_id = worker.last_execution_id
            for execution_id, item in filter_new_executions(items, worker.last_execution_id):
                order_id = str(item.get("order_id", "")).strip()
                if order_id:
                    claimed = await worker.claim_order(order_id)
                    if not claimed:
                        next_last_execution_id = execution_id
                        continue
                    claimed_order_ids.append(order_id)
                payload = build_matching_execution_payload(
                    account_id=settings.strategy_account_id,
                    execution=item,
                )
                publish_batch.append(
                    PublishedEvent(
                        channel=channel,
                        event_type="matching.execution.filled",
                        payload=payload,
                        correlation_id=order_id or None,
                    )
                )
                next_last_execution_id = execution_id

            if publish_batch:
                try:
                    await publish_events_batch(worker, publish_batch)
                except Exception:
                    await release_claimed_orders(worker, claimed_order_ids)
                    raise
                worker.forwarded_executions += len(publish_batch)
            worker.last_execution_id = next_last_execution_id
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            worker.last_error = f"execution relay: {exc}"
            logger.warning("execution relay failed: %s", exc)

        await asyncio.sleep(max(settings.execution_relay_interval_seconds, 0.1))


class PublishedEvent:
    def __init__(
        self,
        *,
        channel: str,
        event_type: str,
        payload: dict[str, Any],
        correlation_id: str | None = None,
    ) -> None:
        self.channel = channel
        self.event_type = event_type
        self.payload = payload
        self.correlation_id = correlation_id


async def release_claimed_orders(worker: RedisMarketWorker, order_ids: list[str]) -> None:
    for order_id in order_ids:
        await worker.release_order_claim(order_id)


async def publish_event(
    *,
    worker: RedisMarketWorker,
    channel: str,
    event_type: str,
    payload: dict[str, Any],
    correlation_id: str | None = None,
) -> None:
    await publish_events_batch(
        worker,
        [
            PublishedEvent(
                channel=channel,
                event_type=event_type,
                payload=payload,
                correlation_id=correlation_id,
            )
        ],
    )


async def publish_events_batch(worker: RedisMarketWorker, events: list[PublishedEvent]) -> None:
    if worker._redis is None or not events:
        return

    pipe = worker._redis.pipeline(transaction=False)
    for event in events:
        if settings.event_stream_enabled:
            envelope = build_event_envelope(event)
            pipe.xadd(
                settings.event_stream_key,
                {"data": json.dumps(envelope, separators=(",", ":"))},
                maxlen=max(settings.event_stream_maxlen, 1),
                approximate=True,
            )
        if settings.event_stream_publish_legacy_pubsub:
            pipe.publish(event.channel, json.dumps(event.payload, separators=(",", ":")))
    await pipe.execute()


def build_event_envelope(event: PublishedEvent) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    envelope: dict[str, Any] = {
        "event_type": event.event_type,
        "event_id": f"evt-{uuid4().hex}",
        "created_at": now,
        "schema_version": settings.event_schema_version,
        "channel": event.channel,
        "payload": event.payload,
    }
    if event.correlation_id:
        envelope["correlation_id"] = event.correlation_id
    return envelope


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
