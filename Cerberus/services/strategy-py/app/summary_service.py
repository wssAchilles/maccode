from __future__ import annotations

from typing import Any

from app.application import SummaryApplicationService


class StrategySummaryService:
    def __init__(self, *, application: SummaryApplicationService) -> None:
        self._application = application

    async def summary(
        self,
        *,
        symbol: str,
        recent_limit: int,
        source: str,
        orderbook_depth: int,
        request_id: str,
    ) -> dict[str, Any]:
        return await self._application.summary(
            symbol=symbol,
            recent_limit=recent_limit,
            source=source,
            orderbook_depth=orderbook_depth,
            request_id=request_id,
        )
