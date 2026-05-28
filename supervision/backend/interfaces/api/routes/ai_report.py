from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from application.usecases.generate_report import GenerateReportUseCase
from shared.schemas.common import ResponseWrapper

router = APIRouter(tags=["ai-report"])


class AIReportRequest(BaseModel):
    stats: dict[str, Any] = Field(description="FrameReport JSON from the CV pipeline")


@router.post("/ai/report", response_model=ResponseWrapper[dict[str, Any]])
def generate_ai_report(request: AIReportRequest) -> ResponseWrapper[dict[str, Any]]:
    result = GenerateReportUseCase().execute(request.stats)
    return ResponseWrapper.success_response(result.to_dict())
