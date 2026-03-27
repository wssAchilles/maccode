from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from app.config import settings
from app.execution_event_payloads import build_matching_execution_payload
from app.execution_relay import filter_new_executions

from .model import PublishedEvent
from .publish import publish_events_batch

if TYPE_CHECKING:
    from app.redis_worker import RedisMarketWorker

logger = logging.getLogger(__name__)


async def run_execution_relay_loop(worker: RedisMarketWorker) -> None:
    if not worker.matching_client.enabled or worker.redis_client is None:
        return

    channel = f"{settings.trade_execution_channel_prefix}.{settings.strategy_account_id}"
    while True:
        try:
            await relay_execution_once(worker, channel)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            worker.set_last_error(f"execution relay: {exc}")
            logger.warning("execution relay failed: %s", exc)

        await asyncio.sleep(max(settings.execution_relay_interval_seconds, 0.1))


async def relay_execution_once(worker: RedisMarketWorker, channel: str) -> None:
    items = await worker.matching_client.list_recent_executions(
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
        worker.increment_forwarded_executions(len(publish_batch))
    worker.update_last_execution_id(next_last_execution_id)


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
