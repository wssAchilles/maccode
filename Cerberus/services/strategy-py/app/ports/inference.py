from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class InferenceDecision:
    signal: str
    confidence: float
    metadata: dict[str, Any] = field(default_factory=dict)


class InferenceEnginePort(Protocol):
    async def infer_signal(
        self,
        *,
        symbol: str,
        price: float,
        quantity: float,
        event_time: str,
    ) -> InferenceDecision | None: ...
