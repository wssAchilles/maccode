from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from app.config import settings
from app.execution_event_payloads import (
    build_matching_execution_payload,
    build_matching_submission_payload,
)
from app.execution_relay import filter_new_executions

if TYPE_CHECKING:
    from app.redis_worker import RedisMarketWorker
    from app.schemas import Signal, TickEvent

logger = logging.getLogger(__name__)


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


def build_signal_event(signal: Signal, tick: TickEvent, signal_id: str) -> PublishedEvent:
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
    return PublishedEvent(
        channel=settings.signal_channel,
        event_type="strategy.signal.generated",
        payload=payload,
        correlation_id=signal_id,
    )


async def publish_signal_event(
    worker: RedisMarketWorker,
    signal: Signal,
    tick: TickEvent,
    signal_id: str,
) -> None:
    await publish_events_batch(worker, [build_signal_event(signal, tick, signal_id)])


async def build_matching_submission_event(
    worker: RedisMarketWorker,
    signal: Signal,
    tick_price: float,
    signal_id: str,
) -> tuple[PublishedEvent | None, str | None]:
    if worker._redis is None:
        return None, None

    claimed_order_id: str | None = None
    try:
        order_event = await worker._matching.submit_from_signal(
            signal, tick_price, idempotency_key=signal_id
        )
        if order_event is None:
            return None, None
        order_id = str(order_event.get("order_id", "")).strip()
        if order_id:
            if not await worker.claim_order(order_id):
                return None, None
            claimed_order_id = order_id
        channel = f"{settings.trade_execution_channel_prefix}.{settings.strategy_account_id}"
        payload = build_matching_submission_payload(
            strategy_id=signal.strategy_id,
            account_id=settings.strategy_account_id,
            order_event=order_event,
        )
        payload["signal_id"] = signal_id
        return (
            PublishedEvent(
                channel=channel,
                event_type="matching.order.submitted",
                payload=payload,
                correlation_id=signal_id,
            ),
            claimed_order_id,
        )
    except Exception as exc:  # noqa: BLE001
        if claimed_order_id:
            await worker.release_order_claim(claimed_order_id)
        logger.warning("matching submit flow failed: %s", exc)
        return None, None


async def publish_signal_and_matching_submission(
    worker: RedisMarketWorker,
    signal: Signal,
    tick: TickEvent,
    signal_id: str,
) -> None:
    if worker._redis is None:
        return

    signal_event = build_signal_event(signal, tick, signal_id)
    matching_event, claimed_order_id = await build_matching_submission_event(
        worker,
        signal,
        tick.price,
        signal_id,
    )

    events = [signal_event]
    if matching_event is not None:
        events.append(matching_event)

    try:
        await publish_events_batch(worker, events)
    except Exception:  # noqa: BLE001
        if claimed_order_id:
            await worker.release_order_claim(claimed_order_id)
        raise


async def publish_matching_submission(
    worker: RedisMarketWorker,
    signal: Signal,
    tick_price: float,
    signal_id: str,
) -> None:
    event, claimed_order_id = await build_matching_submission_event(
        worker,
        signal,
        tick_price,
        signal_id,
    )
    if event is None:
        return
    try:
        await publish_events_batch(worker, [event])
    except Exception as exc:  # noqa: BLE001
        if claimed_order_id:
            await worker.release_order_claim(claimed_order_id)
        logger.warning("matching submit flow failed: %s", exc)


async def run_execution_relay_loop(worker: RedisMarketWorker) -> None:
    if not worker._matching.enabled or worker._redis is None:
        return

    channel = f"{settings.trade_execution_channel_prefix}.{settings.strategy_account_id}"
    while True:
        try:
            await relay_execution_once(worker, channel)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            worker.last_error = f"execution relay: {exc}"
            logger.warning("execution relay failed: %s", exc)

        await asyncio.sleep(max(settings.execution_relay_interval_seconds, 0.1))


async def relay_execution_once(worker: RedisMarketWorker, channel: str) -> None:
    items = await worker._matching.list_recent_executions(
        account_id=settings.strategy_account_id,
        limit=max(settings.execution_relay_batch_limit, 1),
    )
    publish_batch, claimed_order_ids, next_last_execution_id = await build_execution_publish_batch(
        worker,
        channel,
        items,
    )
    if publish_batch:
        try:
            await publish_events_batch(worker, publish_batch)
        except Exception:  # noqa: BLE001
            await release_claimed_orders(worker, claimed_order_ids)
            raise
        worker.forwarded_executions += len(publish_batch)
    worker.last_execution_id = next_last_execution_id


async def build_execution_publish_batch(
    worker: RedisMarketWorker,
    channel: str,
    items: list[dict[str, Any]],
) -> tuple[list[PublishedEvent], list[str], int]:
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
    return publish_batch, claimed_order_ids, next_last_execution_id


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
