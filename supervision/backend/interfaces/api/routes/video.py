from __future__ import annotations

from typing import Any

from application.usecases.process_video import ProcessVideoUseCase
from application.usecases.upload_video import UploadVideoUseCase
from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field
from shared.schemas.common import ResponseWrapper

router = APIRouter(tags=["video"])


class ProcessVideoRequest(BaseModel):
    source: str = Field(default="demo://traffic")


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
