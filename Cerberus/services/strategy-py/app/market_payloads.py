from __future__ import annotations

import json
import logging

from app.schemas import TickEvent

logger = logging.getLogger(__name__)


def market_channels_from_settings(raw_channels: str, fallback_channel: str) -> list[str]:
    if raw_channels.strip():
        return [item.strip() for item in raw_channels.split(",") if item.strip()]
    return [fallback_channel]


def symbol_from_channel(channel: str | None) -> str | None:
    if not channel:
        return None
    parts = channel.split(".")
    if len(parts) < 3:
        return None
    return parts[-1]


def parse_tick_payload(raw: str, channel: str | None) -> TickEvent | None:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        logger.debug("invalid market payload json")
        return None

    if not isinstance(payload, dict):
        return None

    if "price" in payload:
        return _parse_normalized_tick(payload, channel)
    if "bid_price" in payload and "ask_price" in payload:
        return _parse_orderbook_tick(payload, channel)
    return None


def _parse_normalized_tick(payload: dict[str, object], channel: str | None) -> TickEvent | None:
    try:
        tick = TickEvent.model_validate(payload)
        if not tick.symbol and channel:
            channel_symbol = symbol_from_channel(channel)
            if channel_symbol:
                tick.symbol = channel_symbol
        return tick
    except Exception:
        logger.debug("tick payload validation failed")
        return None


def _parse_orderbook_tick(payload: dict[str, object], channel: str | None) -> TickEvent | None:
    try:
        bid = float(payload["bid_price"])
        ask = float(payload["ask_price"])
        symbol = str(payload.get("symbol") or symbol_from_channel(channel) or "BTCUSDT")
        event_time = str(payload.get("event_time", ""))
        return TickEvent(
            symbol=symbol,
            price=(bid + ask) / 2.0,
            quantity=0.0,
            event_time=event_time,
        )
    except Exception:
        logger.debug("orderbook payload conversion failed")
        return None
