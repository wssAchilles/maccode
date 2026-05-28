from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from domain.tracking.models import Track


@dataclass(frozen=True)
class Detection:
    xyxy: list[float]
    confidence: float
    class_id: int
    class_name: str

    def __post_init__(self) -> None:
        if len(self.xyxy) != 4:
            raise ValueError("xyxy must contain [x1, y1, x2, y2]")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")

    @property
    def center(self) -> tuple[float, float]:
        x1, y1, x2, y2 = self.xyxy
        return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)

    @property
    def bottom_center(self) -> tuple[float, float]:
        x1, _, x2, y2 = self.xyxy
        return ((x1 + x2) / 2.0, y2)

    def to_track(self, tracker_id: int, frame_index: int = 0) -> Track:
        from domain.tracking.models import Track

        return Track(
            tracker_id=tracker_id,
            class_id=self.class_id,
            class_name=self.class_name,
            confidence=self.confidence,
            xyxy=list(self.xyxy),
            first_seen_frame=frame_index,
            last_seen_frame=frame_index,
        )


@dataclass(frozen=True)
class Detections:
    items: list[Detection]
    frame_index: int
    timestamp_sec: float

    @classmethod
    def from_raw(
        cls,
        raw_items: Sequence[dict[str, object]],
        frame_index: int,
        timestamp_sec: float,
        confidence_threshold: float,
        allowed_class_ids: set[int] | None = None,
    ) -> Detections:
        detections: list[Detection] = []
        for raw in raw_items:
            class_id = int(cast(int | str, raw["class_id"]))
            confidence = float(cast(float | int | str, raw["confidence"]))
            if confidence < confidence_threshold:
                continue
            if allowed_class_ids is not None and class_id not in allowed_class_ids:
                continue
            xyxy_raw = cast(Sequence[float | int | str], raw["xyxy"])
            detections.append(
                Detection(
                    xyxy=[float(value) for value in xyxy_raw],
                    confidence=confidence,
                    class_id=class_id,
                    class_name=str(raw.get("class_name", class_id)),
                )
            )
        return cls(items=detections, frame_index=frame_index, timestamp_sec=timestamp_sec)
