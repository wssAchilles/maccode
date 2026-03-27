from __future__ import annotations

from app.ports import OptimizationServicePort
from app.schemas import OptimizeRequest, OptimizeResponse


class OptimizationApplicationService:
    def __init__(self, *, optimizer: OptimizationServicePort) -> None:
        self._optimizer = optimizer

    def mean_variance(self, payload: OptimizeRequest) -> OptimizeResponse:
        return self._optimizer.optimize_portfolio(payload)
