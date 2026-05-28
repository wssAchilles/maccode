from __future__ import annotations

from typing import Any

from fastapi import UploadFile

from application.services.runtime_state import DemoRuntime
from application.services.video_upload_store import LocalVideoUploadStore


class UploadVideoUseCase:
    def __init__(self, runtime: DemoRuntime, upload_store: LocalVideoUploadStore) -> None:
        self.runtime = runtime
        self.upload_store = upload_store

    async def upload_and_start(self, file: UploadFile) -> dict[str, Any]:
        uploaded = await self.upload_store.save(file)
        task = self.runtime.start_task(uploaded.source)
        return task.to_dict() | uploaded.to_dict()
