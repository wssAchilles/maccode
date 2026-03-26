from __future__ import annotations

from typing import Any


def filter_execution_items(
    items: list[dict[str, Any]],
    *,
    symbol: str | None,
    order_id: str | None,
    request_id_filter: str | None,
) -> list[dict[str, Any]]:
    filtered = items
    normalized_symbol = (symbol or "").strip().upper()
    if normalized_symbol:
        filtered = [
            item
            for item in filtered
            if str(item.get("symbol", "")).upper() == normalized_symbol
        ]

    normalized_order_id = (order_id or "").strip()
    if normalized_order_id:
        filtered = [
            item for item in filtered if str(item.get("order_id", "")) == normalized_order_id
        ]

    normalized_request_id = (request_id_filter or "").strip()
    if normalized_request_id:
        filtered = [
            item
            for item in filtered
            if str(item.get("request_id", "")) == normalized_request_id
        ]

    return filtered
