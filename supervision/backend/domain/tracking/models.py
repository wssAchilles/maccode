from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class Track:
    tracker_id: int
    class_id: int
    class_name: str
    confidence: float
    xyxy: list[float]
    first_seen_frame: int
    last_seen_frame: int
    speed_kmh: float | None = None

    @property
    def center(self) -> tuple[float, float]:
        x1, y1, x2, y2 = self.xyxy
        return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)

    @property
    def bottom_center(self) -> tuple[float, float]:
        x1, _, x2, y2 = self.xyxy
        return ((x1 + x2) / 2.0, y2)

    def with_detection(self, xyxy: list[float], confidence: float, frame_index: int) -> Track:
        return replace(
            self,
            xyxy=list(xyxy),
            confidence=confidence,
            last_seen_frame=frame_index,
        )

    def with_speed(self, speed_kmh: float | None) -> Track:
        return replace(self, speed_kmh=speed_kmh)
