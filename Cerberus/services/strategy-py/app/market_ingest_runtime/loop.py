from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from app.config import settings

from .pubsub_runtime import run_market_pubsub_loop
from .stream_runtime import run_market_stream_loop

if TYPE_CHECKING:
    from app.redis_worker import RedisMarketWorker

logger = logging.getLogger(__name__)


async def run_market_loop(worker: RedisMarketWorker) -> None:
    assert worker.redis_client is not None
    if settings.market_stream_enabled:
        try:
            await run_market_stream_loop(worker)
            return
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            worker.set_last_error(f"market stream: {exc}")
            worker.mark_market_stream_fallback()
            logger.warning("market stream loop failed, fallback to pubsub: %s", exc)
            if not settings.market_stream_legacy_pubsub_fallback:
                raise

    await run_market_pubsub_loop(worker)


__all__ = ["run_market_loop"]
