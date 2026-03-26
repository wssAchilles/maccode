from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from app.config import settings
from app.market_payloads import market_channels_from_settings

from .retry import compute_backoff_seconds, is_retriable_error
from .stream_processing import parse_tick_message

if TYPE_CHECKING:
    from app.redis_worker import RedisMarketWorker

logger = logging.getLogger(__name__)


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


__all__ = ["run_market_pubsub_loop"]
