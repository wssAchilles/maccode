from __future__ import annotations

from typing import Protocol

from app.schemas import OptimizeRequest, OptimizeResponse


class OptimizationServicePort(Protocol):
    def optimize_portfolio(self, req: OptimizeRequest) -> OptimizeResponse: ...
