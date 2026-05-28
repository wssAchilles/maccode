from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile


@dataclass(frozen=True)
class UploadedVideo:
    uploaded_filename: str
    stored_filename: str
    path: str
    source: str
    content_type: str | None
    size_bytes: int

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class LocalVideoUploadStore:
    allowed_suffixes = {".avi", ".mkv", ".mov", ".mp4", ".webm"}

    def __init__(self, root: Path | str = "data/uploads") -> None:
        self.root = Path(root)

    async def save(self, file: UploadFile) -> UploadedVideo:
        original_filename = Path(file.filename or "").name
        suffix = Path(original_filename).suffix.lower()
        if suffix not in self.allowed_suffixes:
            raise ValueError("unsupported video file type")

        payload = await file.read()
        stored_filename = f"{uuid4().hex}{suffix}"
        self.root.mkdir(parents=True, exist_ok=True)
        stored_path = (self.root / stored_filename).resolve()
        stored_path.write_bytes(payload)

        return UploadedVideo(
            uploaded_filename=original_filename,
            stored_filename=stored_filename,
            path=str(stored_path),
            source=f"file://{stored_path}",
            content_type=file.content_type,
            size_bytes=len(payload),
        )
