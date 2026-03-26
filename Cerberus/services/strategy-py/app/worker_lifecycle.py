from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import TYPE_CHECKING

from redis.asyncio import Redis

from app.config import settings
from app.market_ingest_runtime import run_market_loop

if TYPE_CHECKING:
    from app.redis_worker import RedisMarketWorker

logger = logging.getLogger(__name__)


async def start_worker(worker: RedisMarketWorker) -> None:
    worker._started = True
    if not settings.redis_url.strip():
        logger.warning("REDIS_URL is empty; strategy worker disabled")
        return

    worker._redis = Redis.from_url(settings.redis_url, decode_responses=True)
    worker.market_ingest_mode = "starting"
    worker._task = asyncio.create_task(
        run_market_supervisor_loop(worker),
        name="redis-market-worker",
    )
    if worker._matching.enabled:
        worker._execution_task = asyncio.create_task(
            worker._run_execution_relay_loop(),
            name="matching-execution-relay",
        )


async def stop_worker(worker: RedisMarketWorker) -> None:
    if worker._execution_task:
        worker._execution_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await worker._execution_task

    if worker._task:
        worker._task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await worker._task

    if worker._redis:
        await worker._redis.aclose()

    await worker._supabase.aclose()
    await worker._matching.aclose()
    worker._started = False
    worker.market_ingest_mode = "stopped"


async def run_market_supervisor_loop(worker: RedisMarketWorker) -> None:
    consecutive_failures = 0
    while True:
        try:
            await run_market_loop(worker)
            consecutive_failures = 0
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            consecutive_failures += 1
            worker.last_error = f"market loop: {exc}"
            delay_seconds = min(2 ** max(consecutive_failures - 1, 0), 15)
            logger.warning(
                "market worker loop failed (attempt=%s, backoff=%ss): %s",
                consecutive_failures,
                delay_seconds,
                exc,
            )
            await asyncio.sleep(delay_seconds)
