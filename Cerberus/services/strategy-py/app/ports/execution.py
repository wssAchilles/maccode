from __future__ import annotations

from typing import Protocol

from app.schemas import Signal
from app.schemas import MatchingSubmitResponse


class ExecutionGatewayPort(Protocol):
    async def submit_from_signal(
        self,
        signal: Signal,
        price: float,
        idempotency_key: str | None = None,
    ) -> MatchingSubmitResponse | None: ...
