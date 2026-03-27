from __future__ import annotations

from typing import Any, Protocol

from app.schemas import Signal


class ExecutionGatewayPort(Protocol):
    async def submit_from_signal(
        self,
        signal: Signal,
        price: float,
        idempotency_key: str | None = None,
    ) -> dict[str, Any] | None: ...
