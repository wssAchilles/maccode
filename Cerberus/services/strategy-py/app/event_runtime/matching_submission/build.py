from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.config import settings
from app.execution_event_payloads import build_matching_submission_payload

from app.event_runtime.model import PublishedEvent

if TYPE_CHECKING:
    from app.redis_worker import RedisMarketWorker
    from app.schemas import Signal

logger = logging.getLogger(__name__)


async def build_matching_submission_event(
    worker: RedisMarketWorker,
    signal: Signal,
    tick_price: float,
    signal_id: str,
) -> tuple[PublishedEvent | None, str | None]:
    if worker.redis_client is None:
        return None, None

    claimed_order_id: str | None = None
    try:
        order_event = await worker.matching_client.submit_from_signal(
            signal, tick_price, idempotency_key=signal_id
        )
        if order_event is None:
            return None, None

        claimed, claimed_order_id = await claim_matching_order(worker, order_event)
        if not claimed:
            return None, None

        payload = build_submission_payload(signal, order_event, signal_id)
        return (
            PublishedEvent(
                channel=build_submission_channel(),
                event_type="matching.order.submitted",
                payload=payload,
                correlation_id=signal_id,
            ),
            claimed_order_id or None,
        )
    except Exception as exc:  # noqa: BLE001
        if claimed_order_id:
            await worker.release_order_claim(claimed_order_id)
        logger.warning("matching submit flow failed: %s", exc)
        return None, None


async def claim_matching_order(
    worker: RedisMarketWorker,
    order_event: dict[str, object],
) -> tuple[bool, str | None]:
    order_id = str(order_event.get("order_id", "")).strip()
    if not order_id:
        return True, None
    if not await worker.claim_order(order_id):
        return False, None
    return True, order_id


def build_submission_channel() -> str:
    return f"{settings.trade_execution_channel_prefix}.{settings.strategy_account_id}"


def build_submission_payload(
    signal: Signal,
    order_event: dict[str, object],
    signal_id: str,
) -> dict[str, object]:
    payload = build_matching_submission_payload(
        strategy_id=signal.strategy_id,
        account_id=settings.strategy_account_id,
        order_event=order_event,
    )
    payload["signal_id"] = signal_id
    return payload


__all__ = ["build_matching_submission_event"]
