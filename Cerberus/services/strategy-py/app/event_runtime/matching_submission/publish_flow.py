from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.event_runtime.publish import (
    build_signal_event,
    publish_events_batch,
)

from .build import build_matching_submission_event

if TYPE_CHECKING:
    from app.redis_worker import RedisMarketWorker
    from app.schemas import Signal, TickEvent

logger = logging.getLogger(__name__)


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


__all__ = ["publish_matching_submission", "publish_signal_and_matching_submission"]
