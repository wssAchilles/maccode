from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from app.config import settings

from .envelope import build_event_envelope
from .model import PublishedEvent

if TYPE_CHECKING:
    from app.redis_worker import RedisMarketWorker
    from app.schemas import Signal, TickEvent


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
    redis = worker.redis_client
    if redis is None or not events:
        return

    pipe = redis.pipeline(transaction=False)
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
