from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.schemas import MatchingOrderBookView, MatchingStatsView


def build_degraded_stats(*, request_id: str, reason: str) -> MatchingStatsView:
    return MatchingStatsView(
        enabled=True,
        degraded=True,
        live_orders=0,
        trade_count=0,
        tracked_orders=0,
        rejected_orders=0,
        symbols=0,
        best_bid=None,
        best_ask=None,
        request_id=request_id,
        reason=reason,
    )


def build_degraded_orderbook(
    *,
    symbol: str,
    depth: int,
    request_id: str,
    reason: str,
) -> MatchingOrderBookView:
    return MatchingOrderBookView(
        enabled=True,
        degraded=True,
        symbol=symbol,
        depth=depth,
        bids=[],
        asks=[],
        generated_at_ms=0,
        request_id=request_id,
        reason=reason,
    )


def mark_orderbook_degraded_if_empty(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    normalized = dict(payload.items())
    if normalized.get("bids") or normalized.get("asks"):
        return normalized
    normalized["degraded"] = normalized.get("degraded", True)
    normalized["reason"] = normalized.get("reason") or "orderbook empty"
    return normalized

