from fastapi import APIRouter

from app.inference_service import InferenceService


def build_inference_router(service: InferenceService) -> APIRouter:
    router = APIRouter()

    @router.get("/api/v1/inference/status")
    async def inference_status() -> dict[str, object]:
        return await service.status()

    @router.get("/api/v1/inference/models")
    async def inference_models() -> dict[str, object]:
        return service.models()

    return router
