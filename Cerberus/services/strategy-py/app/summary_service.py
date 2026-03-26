from __future__ import annotations

import asyncio
from typing import Any

from app.api.summary_helpers import (
    build_matching_orderbook_component,
    build_persistence_component,
    build_recent_signals_component,
    build_signal_component,
    normalize_source,
    normalize_symbol,
)
from app.redis_worker import RedisMarketWorker
from app.signal_store import SignalStore


class StrategySummaryService:
    def __init__(self, *, worker: RedisMarketWorker, signal_store: SignalStore) -> None:
        self._worker = worker
        self._signal_store = signal_store

    async def summary(
        self,
        *,
        symbol: str,
        recent_limit: int,
        source: str,
        orderbook_depth: int,
        request_id: str,
    ) -> dict[str, Any]:
        normalized_symbol = normalize_symbol(symbol)
        selected_source = normalize_source(source)

        signal_component = build_signal_component(self._worker)
        recent_component, persistence_component, orderbook_component = await asyncio.gather(
            build_recent_signals_component(
                self._signal_store,
                limit=recent_limit,
                source=selected_source,
                request_id=request_id,
            ),
            build_persistence_component(
                self._worker,
                self._signal_store,
                request_id=request_id,
            ),
            build_matching_orderbook_component(
                self._worker,
                symbol=normalized_symbol,
                depth=orderbook_depth,
                request_id=request_id,
            ),
        )

        return {
            "symbol": normalized_symbol,
            "source": selected_source,
            "recent_limit": recent_limit,
            "orderbook_depth": orderbook_depth,
            "signal": signal_component,
            "recent_signals": recent_component,
            "persistence": persistence_component,
            "matching_orderbook": orderbook_component,
        }
