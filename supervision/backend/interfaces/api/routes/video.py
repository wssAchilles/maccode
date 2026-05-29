from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from application.usecases.process_video import ProcessVideoUseCase
from application.usecases.upload_video import UploadVideoUseCase
from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field
from shared.schemas.common import ResponseWrapper

router = APIRouter(tags=["video"])
PROJECT_ROOT = Path(__file__).resolve().parents[4]
GOLDEN_CLIPS_PATH = PROJECT_ROOT / "data/tests/golden_clips.yaml"
GOLDEN_TUNING_PATH = PROJECT_ROOT / "data/tests/golden_tuning.yaml"


class ProcessVideoRequest(BaseModel):
    source: str = Field(default="demo://traffic")


def _sample_profile_for_name(name: str) -> str:
    if "pedestrian" in name:
        return "pedestrian_high_view"
    if "dense_city_traffic_4k" in name:
        return "dense_city_traffic_4k"
    if "red_light" in name:
        return "red_light_static"
    return "wide_signalized_intersection"


def _load_golden_clips() -> list[dict[str, str]]:
    if not GOLDEN_CLIPS_PATH.exists():
        return []
    payload = yaml.safe_load(GOLDEN_CLIPS_PATH.read_text()) or {}
    clips = payload.get("clips", [])
    return [clip for clip in clips if isinstance(clip, dict) and clip.get("name")]


def _load_golden_tuning() -> dict[str, Any]:
    if not GOLDEN_TUNING_PATH.exists():
        return {}
    payload = yaml.safe_load(GOLDEN_TUNING_PATH.read_text()) or {}
    clips = payload.get("clips", {})
    return clips if isinstance(clips, dict) else {}


@router.post("/video/process", response_model=ResponseWrapper[dict[str, Any]])
def process_video(
    request: ProcessVideoRequest,
    app_request: Request,
) -> ResponseWrapper[dict[str, Any]]:
    task = ProcessVideoUseCase(app_request.app.state.runtime).start(request.source)
    return ResponseWrapper.success_response(task.to_dict())


@router.post("/video/upload", response_model=ResponseWrapper[dict[str, Any]])
async def upload_video(
    app_request: Request,
    file: UploadFile = File(...),
) -> ResponseWrapper[dict[str, Any]]:
    try:
        payload = await UploadVideoUseCase(
            app_request.app.state.runtime,
            app_request.app.state.video_upload_store,
        ).upload_and_start(file)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ResponseWrapper.success_response(payload)


@router.get("/video/samples", response_model=ResponseWrapper[list[dict[str, Any]]])
def list_video_samples() -> ResponseWrapper[list[dict[str, Any]]]:
    samples_dir = PROJECT_ROOT / "data/tests/real_video_clips"
    golden_clips = _load_golden_clips()
    golden_tuning = _load_golden_tuning()
    if golden_clips:
        paths = [samples_dir / str(clip["name"]) for clip in golden_clips]
    else:
        paths = sorted(samples_dir.glob("*.mp4"))
    samples = []
    for index, path in enumerate(paths):
        if not path.exists():
            continue
        golden_clip = golden_clips[index] if golden_clips else {}
        tuning = golden_tuning.get(path.name, {})
        samples.append(
            {
                "name": path.name,
                "source": f"file://{path.resolve()}",
                "profile": str(
                    golden_clip.get("profile") or _sample_profile_for_name(path.name),
                ),
                "role": golden_clip.get("role"),
                "selection_reason": golden_clip.get("selection_reason"),
                "tuning": tuning if isinstance(tuning, dict) else {},
                "size_bytes": path.stat().st_size,
            },
        )
    return ResponseWrapper.success_response(samples)


@router.get("/video/status/{task_id}", response_model=ResponseWrapper[dict[str, Any]])
def get_video_status(task_id: str, request: Request) -> ResponseWrapper[dict[str, Any]]:
    task = ProcessVideoUseCase(request.app.state.runtime).get_status(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    return ResponseWrapper.success_response(task.to_dict())


@router.post("/video/stop/{task_id}", response_model=ResponseWrapper[dict[str, Any]])
def stop_video(task_id: str, request: Request) -> ResponseWrapper[dict[str, Any]]:
    task = ProcessVideoUseCase(request.app.state.runtime).stop(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    return ResponseWrapper.success_response(task.to_dict())
