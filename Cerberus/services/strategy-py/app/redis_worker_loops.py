from __future__ import annotations

import asyncio
import json
import logging
from typing import TYPE_CHECKING

from app.config import settings
from app.execution_relay import filter_new_executions
from app.market_payloads import market_channels_from_settings, parse_tick_payload

if TYPE_CHECKING:
    from app.redis_worker import RedisMarketWorker
    from app.schemas import Signal

logger = logging.getLogger(__name__)


async def run_market_loop(worker: RedisMarketWorker) -> None:
    assert worker._redis is not None
    pubsub = worker._redis.pubsub()
    channels = market_channels_from_settings(settings.market_channels, settings.market_channel)
    await pubsub.subscribe(*channels)
    logger.info("Subscribed to market channels: %s", ", ".join(channels))

    try:
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if not message:
                await asyncio.sleep(0.05)
                continue

            raw = message.get("data")
            if not isinstance(raw, str):
                continue

            channel = message.get("channel")
            tick = parse_tick_payload(raw, str(channel) if isinstance(channel, str) else None)
            if tick is None:
                continue

            try:
                await worker.ingest_tick(tick)
            except Exception as exc:
                worker.last_error = str(exc)
                logger.warning("tick ingest failed: %s", exc)
    finally:
        await pubsub.unsubscribe(*channels)
        await pubsub.aclose()  # type: ignore[no-untyped-call]


async def publish_matching_submission(worker: RedisMarketWorker, signal: Signal, tick_price: float) -> None:
    if worker._redis is None:
        return

    try:
        order_event = await worker._matching.submit_from_signal(signal, tick_price)
        if order_event is None:
            return
        channel = f"{settings.trade_execution_channel_prefix}.{settings.strategy_account_id}"
        payload = {
            "event": "order_submitted",
            "strategy_id": signal.strategy_id,
            **order_event,
        }
        await worker._redis.publish(channel, json.dumps(payload))
    except Exception as exc:
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
            for execution_id, item in filter_new_executions(items, worker.last_execution_id):
                payload = {
                    "event": "execution_report",
                    "account_id": settings.strategy_account_id,
                    **item,
                }
                await worker._redis.publish(channel, json.dumps(payload))
                worker.last_execution_id = execution_id
                worker.forwarded_executions += 1
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            worker.last_error = f"execution relay: {exc}"
            logger.warning("execution relay failed: %s", exc)

        await asyncio.sleep(max(settings.execution_relay_interval_seconds, 0.1))
