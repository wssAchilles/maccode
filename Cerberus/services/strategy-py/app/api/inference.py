from fastapi import APIRouter, Query

from app.inference_service import InferenceService


def build_inference_router(service: InferenceService) -> APIRouter:
    router = APIRouter()

    @router.get("/api/v1/inference/status")
    async def inference_status() -> dict[str, object]:
        return await service.status()

    @router.get("/api/v1/inference/models")
    async def inference_models() -> dict[str, object]:
        return service.models()

    @router.get("/api/v1/inference/audit")
    async def inference_audit(limit: int = Query(default=20, ge=1, le=100)) -> dict[str, object]:
        return service.audit(limit=limit)

    return router
