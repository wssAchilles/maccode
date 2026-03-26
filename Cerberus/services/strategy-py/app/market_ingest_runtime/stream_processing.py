from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from app.market_payloads import parse_tick_payload

from .retry import is_retriable_error
from .stream_io import ack_market_stream_entries

if TYPE_CHECKING:
    from app.redis_worker import RedisMarketWorker
    from app.schemas import TickEvent

logger = logging.getLogger(__name__)


async def process_market_stream_batch(
    worker: RedisMarketWorker,
    stream_key: str,
    group: str,
    entries: list[tuple[str, dict[str, Any]]],
) -> None:
    ack_ids: list[str] = []
    for stream_id, fields in entries:
        raw_payload, channel = parse_market_stream_entry(fields)
        if raw_payload is None:
            ack_ids.append(stream_id)
            continue

        tick = parse_tick_payload(raw_payload, channel)
        if tick is None:
            ack_ids.append(stream_id)
            continue

        try:
            await worker.ingest_tick(tick)
            ack_ids.append(stream_id)
            worker.market_stream_events += 1
            worker.last_market_stream_id = stream_id
        except Exception as exc:  # noqa: BLE001
            worker.last_error = str(exc)
            if is_retriable_error(exc):
                if ack_ids:
                    await ack_market_stream_entries(worker, stream_key, group, ack_ids)
                raise
            logger.warning("market stream non-retriable ingest failure: %s", exc)
            ack_ids.append(stream_id)

    if ack_ids:
        await ack_market_stream_entries(worker, stream_key, group, ack_ids)


def parse_market_stream_entry(fields: dict[str, Any]) -> tuple[str | None, str | None]:
    raw = fields.get("data") or fields.get("payload") or fields.get("json")
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="ignore")
    if not isinstance(raw, str) or not raw.strip():
        return None, None

    channel = fields.get("channel")
    if isinstance(channel, bytes):
        channel = channel.decode("utf-8", errors="ignore")
    if not isinstance(channel, str):
        channel = None

    return raw, channel


def parse_tick_message(message: dict[str, object]) -> TickEvent | None:
    raw = message.get("data")
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="ignore")
    if not isinstance(raw, str):
        return None

    channel = message.get("channel")
    if isinstance(channel, bytes):
        channel = channel.decode("utf-8", errors="ignore")

    return parse_tick_payload(raw, str(channel) if isinstance(channel, str) else None)


__all__ = [
    "parse_market_stream_entry",
    "parse_tick_message",
    "process_market_stream_batch",
]
