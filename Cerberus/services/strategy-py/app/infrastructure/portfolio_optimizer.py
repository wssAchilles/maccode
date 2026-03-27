from __future__ import annotations

from app.optimizer import optimize_portfolio
from app.schemas import OptimizeRequest, OptimizeResponse


class GurobiPortfolioOptimizer:
    def optimize_portfolio(self, req: OptimizeRequest) -> OptimizeResponse:
        return optimize_portfolio(req)
