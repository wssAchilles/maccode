from __future__ import annotations

from fastapi import APIRouter

from shared.schemas.common import ResponseWrapper

router = APIRouter(tags=["health"])


@router.get("/health", response_model=ResponseWrapper[dict[str, str]])
def health_check() -> ResponseWrapper[dict[str, str]]:
    return ResponseWrapper.success_response(
        {
            "service": "TrafficPerceptionEngine",
            "status": "ok",
            "runtime": "local-m5",
        }
    )
