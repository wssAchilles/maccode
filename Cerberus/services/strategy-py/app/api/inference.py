from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.inference_service import InferenceService


class InferenceActionRequest(BaseModel):
    actor: str | None = Field(default=None, max_length=120)
    reason: str | None = Field(default=None, max_length=500)


class InferenceActivateModelRequest(InferenceActionRequest):
    model_id: str = Field(min_length=1, max_length=200)
    version: str | None = Field(default=None, max_length=120)


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

    @router.post("/api/v1/inference/rollout/promote")
    async def inference_promote(
        body: InferenceActionRequest | None = None,
    ) -> dict[str, object]:
        payload = body or InferenceActionRequest()
        return await service.promote(actor=payload.actor, reason=payload.reason)

    @router.post("/api/v1/inference/rollout/rollback")
    async def inference_rollback(
        body: InferenceActionRequest | None = None,
    ) -> dict[str, object]:
        payload = body or InferenceActionRequest()
        return await service.rollback(actor=payload.actor, reason=payload.reason)

    @router.post("/api/v1/inference/models/activate")
    async def inference_activate_model(
        body: InferenceActivateModelRequest,
    ) -> dict[str, object]:
        try:
            return await service.activate_model(
                model_id=body.model_id,
                version=body.version,
                actor=body.actor,
                reason=body.reason,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    return router
