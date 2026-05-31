from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GroundContactPoint:
    pixel: tuple[float, float]
    raw_pixel: tuple[float, float]
    confidence: float
    source: str


@dataclass
class _ContactState:
    pixel: tuple[float, float]
    timestamp_sec: float


class GroundContactCorrector:
    """Stabilize the image-plane ground contact point used for homography speed."""

    VEHICLE_CLASS_IDS = {2, 3, 5, 7}
    PERSON_CLASS_IDS = {0}
    BICYCLE_CLASS_IDS = {1}

    def __init__(self) -> None:
        self._states: dict[int, _ContactState] = {}

    def correct(
        self,
        tracker_id: int,
        class_id: int,
        xyxy: list[float],
        timestamp_sec: float,
    ) -> GroundContactPoint:
        x1, y1, x2, y2 = xyxy
        height = max(y2 - y1, 1.0)
        raw_x = (x1 + x2) / 2.0
        raw_y = y2 - height * self._vertical_inset_ratio(class_id)
        raw_pixel = (float(raw_x), float(raw_y))
        previous = self._states.get(tracker_id)
        if previous is None or timestamp_sec <= previous.timestamp_sec:
            self._states[tracker_id] = _ContactState(raw_pixel, timestamp_sec)
            return GroundContactPoint(
                pixel=raw_pixel,
                raw_pixel=raw_pixel,
                confidence=1.0,
                source="bbox_ground_contact",
            )

        alpha_y = self._vertical_smoothing_alpha(class_id)
        corrected_pixel = (
            raw_pixel[0],
            previous.pixel[1] + alpha_y * (raw_pixel[1] - previous.pixel[1]),
        )
        self._states[tracker_id] = _ContactState(corrected_pixel, timestamp_sec)
        vertical_correction_px = abs(corrected_pixel[1] - raw_pixel[1])
        confidence = max(0.2, min(1.0, 1.0 - vertical_correction_px / height))
        return GroundContactPoint(
            pixel=corrected_pixel,
            raw_pixel=raw_pixel,
            confidence=float(confidence),
            source="temporal_ground_contact_correction",
        )

    @staticmethod
    def _vertical_inset_ratio(class_id: int) -> float:
        if class_id in GroundContactCorrector.VEHICLE_CLASS_IDS:
            return 0.04
        if class_id in GroundContactCorrector.BICYCLE_CLASS_IDS:
            return 0.02
        return 0.0

    @staticmethod
    def _vertical_smoothing_alpha(class_id: int) -> float:
        if class_id in GroundContactCorrector.VEHICLE_CLASS_IDS:
            return 0.22
        if class_id in GroundContactCorrector.BICYCLE_CLASS_IDS:
            return 0.20
        return 0.15
