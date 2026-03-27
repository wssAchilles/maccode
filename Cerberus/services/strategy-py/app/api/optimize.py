from fastapi import APIRouter, HTTPException

from app.application import OptimizationApplicationService
from app.schemas import OptimizeRequest, OptimizeResponse


def build_optimize_router(service: OptimizationApplicationService) -> APIRouter:
    router = APIRouter()

    @router.post("/api/v1/optimize/mean-variance", response_model=OptimizeResponse)
    async def mean_variance_optimize(payload: OptimizeRequest) -> OptimizeResponse:
        try:
            return service.mean_variance(payload)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"optimization failed: {exc}") from exc

    return router
