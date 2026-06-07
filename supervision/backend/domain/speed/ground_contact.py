from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GroundContactPoint:
    pixel: tuple[float, float]
    raw_pixel: tuple[float, float]
    confidence: float
    source: str
    observation_sigma_px: float = 1.0
    measurement_source: str = "bbox_ground_contact"
    fusion_sources: list[str] | None = None
    fusion_weights: dict[str, float] | None = None
    pixel_covariance: list[list[float]] | None = None
    fusion_confidence: float | None = None
    outlier_sources: list[str] | None = None
    innovation_score: float | None = None
    optical_flow_inlier_ratio: float | None = None


@dataclass
class _ContactState:
    pixel: tuple[float, float]
    timestamp_sec: float
    bbox_width: float
    bbox_height: float


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
        width = max(x2 - x1, 1.0)
        height = max(y2 - y1, 1.0)
        raw_x = (x1 + x2) / 2.0
        raw_y = y2 - height * self._vertical_inset_ratio(class_id)
        raw_pixel = (float(raw_x), float(raw_y))
        previous = self._states.get(tracker_id)
        if previous is None or timestamp_sec <= previous.timestamp_sec:
            self._states[tracker_id] = _ContactState(raw_pixel, timestamp_sec, width, height)
            return GroundContactPoint(
                pixel=raw_pixel,
                raw_pixel=raw_pixel,
                confidence=1.0,
                source="bbox_ground_contact",
                observation_sigma_px=self._base_observation_sigma_px(class_id, width, height),
                measurement_source="bbox_ground_contact",
            )

        delta_t = max(timestamp_sec - previous.timestamp_sec, 1e-3)
        alpha_x, alpha_y = self._smoothing_alpha(class_id)
        candidate_pixel = (
            previous.pixel[0] + alpha_x * (raw_pixel[0] - previous.pixel[0]),
            previous.pixel[1] + alpha_y * (raw_pixel[1] - previous.pixel[1]),
        )
        max_step_px = self._max_step_px(class_id, width, height, delta_t)
        corrected_pixel = (
            previous.pixel[0] + self._clamp(candidate_pixel[0] - previous.pixel[0], max_step_px),
            previous.pixel[1] + self._clamp(candidate_pixel[1] - previous.pixel[1], max_step_px),
        )
        self._states[tracker_id] = _ContactState(corrected_pixel, timestamp_sec, width, height)
        correction_px = (
            (corrected_pixel[0] - raw_pixel[0]) ** 2
            + (corrected_pixel[1] - raw_pixel[1]) ** 2
        ) ** 0.5
        size_drift = abs(width - previous.bbox_width) / max(previous.bbox_width, 1.0)
        size_drift += abs(height - previous.bbox_height) / max(previous.bbox_height, 1.0)
        correction_factor = 1.0 - correction_px / max(width, height, 1.0)
        drift_factor = 1.0 - min(size_drift * 0.35, 0.55)
        confidence = max(0.15, min(1.0, correction_factor * drift_factor))
        base_sigma = self._base_observation_sigma_px(class_id, width, height)
        observation_sigma_px = base_sigma * (1.0 + correction_px / max(width, height, 1.0))
        observation_sigma_px *= 1.0 + min(size_drift, 2.0)
        return GroundContactPoint(
            pixel=corrected_pixel,
            raw_pixel=raw_pixel,
            confidence=float(confidence),
            source="temporal_ground_contact_correction",
            observation_sigma_px=float(observation_sigma_px),
            measurement_source="temporal_ground_contact_correction",
        )

    @staticmethod
    def _vertical_inset_ratio(class_id: int) -> float:
        if class_id in GroundContactCorrector.VEHICLE_CLASS_IDS:
            return 0.04
        if class_id in GroundContactCorrector.BICYCLE_CLASS_IDS:
            return 0.02
        return 0.0

    @staticmethod
    def _smoothing_alpha(class_id: int) -> tuple[float, float]:
        if class_id in GroundContactCorrector.VEHICLE_CLASS_IDS:
            return (0.72, 0.24)
        if class_id in GroundContactCorrector.BICYCLE_CLASS_IDS:
            return (0.62, 0.22)
        return (0.45, 0.18)

    @staticmethod
    def _max_step_px(class_id: int, width: float, height: float, delta_t: float) -> float:
        base = max(width, height)
        if class_id in GroundContactCorrector.VEHICLE_CLASS_IDS:
            return max(8.0, base * 0.7, 280.0 * delta_t)
        if class_id in GroundContactCorrector.BICYCLE_CLASS_IDS:
            return max(5.0, base * 0.55, 180.0 * delta_t)
        return max(3.0, base * 0.35, 90.0 * delta_t)

    @staticmethod
    def _clamp(value: float, max_abs: float) -> float:
        return max(-max_abs, min(max_abs, value))

    @staticmethod
    def _base_observation_sigma_px(class_id: int, width: float, height: float) -> float:
        base = max(width, height, 1.0)
        if class_id in GroundContactCorrector.VEHICLE_CLASS_IDS:
            return max(1.0, base * 0.025)
        if class_id in GroundContactCorrector.BICYCLE_CLASS_IDS:
            return max(1.2, base * 0.035)
        return max(1.5, base * 0.045)
