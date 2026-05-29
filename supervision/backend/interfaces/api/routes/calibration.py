from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field
from shared.schemas.common import ResponseWrapper

router = APIRouter(tags=["calibration"])


class CalibrationPointPayload(BaseModel):
    pixel_x: float
    pixel_y: float
    world_x: float
    world_y: float


class CalibrationEntryPayload(BaseModel):
    clip_name: str = Field(description="Exact MP4 filename for the video calibration.")
    notes: str = "Manual calibration from frontend workbench."
    position_rmse_floor_m: float = 1.0
    calibration_scale_uncertainty_pct: float = 5.0
    points: list[CalibrationPointPayload]
    frame_width: int | None = None
    frame_height: int | None = None
    grid_spacing_m: float = 5.0


@router.get("/calibration/presets", response_model=ResponseWrapper[dict[str, Any]])
def list_calibration_presets(request: Request) -> ResponseWrapper[dict[str, Any]]:
    return ResponseWrapper.success_response(
        request.app.state.calibration_preset_store.list_entries(),
    )


@router.get("/calibration/preset", response_model=ResponseWrapper[dict[str, Any] | None])
def get_calibration_preset(
    request: Request,
    clip_name: str = Query(..., min_length=5),
) -> ResponseWrapper[dict[str, Any] | None]:
    return ResponseWrapper.success_response(
        request.app.state.calibration_preset_store.get_entry(clip_name),
    )


@router.put("/calibration/preset", response_model=ResponseWrapper[dict[str, Any]])
def save_calibration_preset(
    payload: CalibrationEntryPayload,
    request: Request,
) -> ResponseWrapper[dict[str, Any]]:
    try:
        saved = request.app.state.calibration_preset_store.upsert_entry(
            payload.clip_name,
            payload.model_dump(
                exclude={"clip_name", "frame_width", "frame_height", "grid_spacing_m"},
            ),
            frame_width=payload.frame_width,
            frame_height=payload.frame_height,
            grid_spacing_m=payload.grid_spacing_m,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ResponseWrapper.success_response(saved)
