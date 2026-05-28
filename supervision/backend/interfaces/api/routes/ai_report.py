from __future__ import annotations

from typing import Any

from application.usecases.generate_report import GenerateReportUseCase
from fastapi import APIRouter
from pydantic import BaseModel, Field
from shared.schemas.common import ResponseWrapper

router = APIRouter(tags=["ai-report"])


class AIReportRequest(BaseModel):
    stats: dict[str, Any] = Field(description="FrameReport JSON from the CV pipeline")
    location_label: str | None = Field(default=None, description="Human scene label")
    scene_tags: list[str] = Field(default_factory=list, description="Atomic context tags")


@router.post("/ai/report", response_model=ResponseWrapper[dict[str, Any]])
def generate_ai_report(request: AIReportRequest) -> ResponseWrapper[dict[str, Any]]:
    result = GenerateReportUseCase().execute(
        request.stats,
        location_label=request.location_label,
        scene_tags=request.scene_tags,
    )
    return ResponseWrapper.success_response(result.to_dict())
