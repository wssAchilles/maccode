from fastapi import APIRouter, HTTPException

from app.optimizer import optimize_portfolio
from app.schemas import OptimizeRequest, OptimizeResponse


def build_optimize_router() -> APIRouter:
    router = APIRouter()

    @router.post("/api/v1/optimize/mean-variance", response_model=OptimizeResponse)
    async def mean_variance_optimize(payload: OptimizeRequest) -> OptimizeResponse:
        try:
            return optimize_portfolio(payload)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"optimization failed: {exc}") from exc

    return router
