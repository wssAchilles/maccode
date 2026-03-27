from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from app.config import settings
from app.market_ingest_runtime.retry import compute_market_stream_backoff_ms
from app.market_ingest_runtime.stream_io import read_market_stream_entries
from app.market_ingest_runtime.stream_processing import process_market_stream_batch
from app.market_ingest_runtime.time_utils import current_epoch_millis

from .maintenance import (
    run_market_stream_maintenance,
    should_run_market_stream_maintenance,
)

if TYPE_CHECKING:
    from app.redis_worker import RedisMarketWorker

logger = logging.getLogger(__name__)


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
                    worker.increment_market_stream_reclaim_failures()
                    worker.set_last_error(f"market stream maintenance: {exc}")
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
            worker.reset_market_stream_retry_state()
            continue
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            consecutive_failures += 1
            backoff_ms = compute_market_stream_backoff_ms(consecutive_failures)
            worker.record_market_stream_retry(
                consecutive_failures=consecutive_failures,
                backoff_ms=backoff_ms,
                message=f"market stream: {exc}",
            )
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


__all__ = ["market_stream_consume_loop"]
