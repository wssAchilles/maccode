from __future__ import annotations

import asyncio
import logging
import socket
from typing import TYPE_CHECKING

from redis.exceptions import RedisError

from app.config import settings

from .retry import compute_market_stream_backoff_ms
from .stream_io import (
    read_market_stream_entries,
    refresh_market_stream_backlog_metrics,
)
from .stream_processing import process_market_stream_batch
from .stream_reclaim import reclaim_market_stream_entries
from .time_utils import current_epoch_millis

if TYPE_CHECKING:
    from app.redis_worker import RedisMarketWorker

logger = logging.getLogger(__name__)


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


def market_stream_consumer_name() -> str:
    configured = settings.market_stream_consumer_name.strip()
    if configured:
        return configured
    host = socket.gethostname().strip() or "local"
    return f"strategy-{host}"


__all__ = [
    "ensure_market_stream_group",
    "market_stream_consume_loop",
    "market_stream_consumer_name",
    "replay_pending_market_stream_entries",
    "run_market_stream_loop",
    "run_market_stream_maintenance",
    "should_run_market_stream_maintenance",
]
