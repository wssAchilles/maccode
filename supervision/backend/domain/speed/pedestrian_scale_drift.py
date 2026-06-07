from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class PedestrianGeometrySample:
    tracker_id: int
    speed_kmh: float
    bbox_top: tuple[float, float]
    bbox_bottom: tuple[float, float]
    bbox_height_px: float
    footpoint_pixel: tuple[float, float]
    pixel_y: float
    local_scale_factor: float
    local_scale_percentile: float
    timestamp_sec: float
    pose_ankle_pixel: tuple[float, float] | None = None
    pose_head_pixel: tuple[float, float] | None = None


@dataclass(frozen=True)
class PedestrianScaleDriftResult:
    scale_drift_detected: bool
    speed_scale_correlation: float | None
    speed_inverse_height_correlation: float | None
    far_near_speed_ratio: float | None
    height_consistency_score: float
    recommended_speed_scale_factor: float | None
    geometry_rejection_reason: str | None
    model_reference: str = "pedestrian_head_foot_scale_drift_v1"

    def to_dict(self) -> dict[str, object]:
        return {
            "scale_drift_detected": self.scale_drift_detected,
            "speed_scale_correlation": self.speed_scale_correlation,
            "speed_inverse_height_correlation": self.speed_inverse_height_correlation,
            "far_near_speed_ratio": self.far_near_speed_ratio,
            "height_consistency_score": self.height_consistency_score,
            "recommended_speed_scale_factor": self.recommended_speed_scale_factor,
            "geometry_rejection_reason": self.geometry_rejection_reason,
            "model_reference": self.model_reference,
        }


class PedestrianScaleDriftAnalyzer:
    def __init__(
        self,
        *,
        min_sample_count: int = 6,
        correlation_threshold: float = 0.60,
        far_near_ratio_threshold: float = 1.50,
        far_scale_percentile_threshold: float = 0.80,
        moderate_speed_kmh: float = 12.0,
        max_stable_speed_kmh: float = 18.0,
    ) -> None:
        self.min_sample_count = min_sample_count
        self.correlation_threshold = correlation_threshold
        self.far_near_ratio_threshold = far_near_ratio_threshold
        self.far_scale_percentile_threshold = far_scale_percentile_threshold
        self.moderate_speed_kmh = moderate_speed_kmh
        self.max_stable_speed_kmh = max_stable_speed_kmh

    def analyze(
        self,
        samples: list[PedestrianGeometrySample],
    ) -> PedestrianScaleDriftResult:
        if len(samples) < self.min_sample_count:
            return PedestrianScaleDriftResult(
                False,
                None,
                None,
                None,
                self._height_consistency_score(samples),
                None,
                None,
            )

        ordered = sorted(samples, key=lambda sample: sample.timestamp_sec)
        speeds = np.asarray([sample.speed_kmh for sample in ordered], dtype=np.float64)
        scales = np.asarray(
            [sample.local_scale_factor for sample in ordered],
            dtype=np.float64,
        )
        heights = np.asarray(
            [max(sample.bbox_height_px, 1e-6) for sample in ordered],
            dtype=np.float64,
        )
        inverse_heights = 1.0 / heights
        percentiles = np.asarray(
            [sample.local_scale_percentile for sample in ordered],
            dtype=np.float64,
        )

        speed_scale_correlation = self._correlation(speeds, scales)
        speed_inverse_height_correlation = self._correlation(speeds, inverse_heights)
        far_near_speed_ratio = self._far_near_speed_ratio(speeds, scales)
        height_consistency_score = self._height_consistency_score(ordered)
        height_decreases = float(heights[-1]) < float(heights[0]) * 0.85
        speed_increases = float(speeds[-1]) > float(speeds[0]) * 1.35
        far_field = float(np.max(percentiles)) >= self.far_scale_percentile_threshold
        max_speed = float(np.max(speeds))

        correlation_drift = (
            far_near_speed_ratio is not None
            and far_near_speed_ratio >= self.far_near_ratio_threshold
            and (
                (speed_scale_correlation or 0.0) >= self.correlation_threshold
                or (speed_inverse_height_correlation or 0.0)
                >= self.correlation_threshold
            )
        )
        sequential_drift = (
            max_speed > self.moderate_speed_kmh
            and speed_increases
            and height_decreases
            and far_field
        )
        direct_far_speed = max_speed > self.max_stable_speed_kmh and far_field
        detected = bool(correlation_drift or sequential_drift or direct_far_speed)
        recommended_scale = (
            self._recommended_scale_factor(speeds, scales)
            if detected
            else None
        )
        return PedestrianScaleDriftResult(
            scale_drift_detected=detected,
            speed_scale_correlation=speed_scale_correlation,
            speed_inverse_height_correlation=speed_inverse_height_correlation,
            far_near_speed_ratio=far_near_speed_ratio,
            height_consistency_score=height_consistency_score,
            recommended_speed_scale_factor=recommended_scale,
            geometry_rejection_reason=(
                "pedestrian_perspective_scale_drift" if detected else None
            ),
        )

    @staticmethod
    def _correlation(left: np.ndarray, right: np.ndarray) -> float | None:
        if left.size < 2 or float(np.std(left)) <= 1e-9 or float(np.std(right)) <= 1e-9:
            return None
        return float(np.corrcoef(left, right)[0, 1])

    @staticmethod
    def _far_near_speed_ratio(
        speeds: np.ndarray,
        scales: np.ndarray,
    ) -> float | None:
        if speeds.size < 2:
            return None
        order = np.argsort(scales)
        bucket_size = max(1, speeds.size // 3)
        near = speeds[order[:bucket_size]]
        far = speeds[order[-bucket_size:]]
        return float(np.mean(far) / max(float(np.mean(near)), 1e-6))

    @staticmethod
    def _height_consistency_score(samples: list[PedestrianGeometrySample]) -> float:
        if not samples:
            return 0.0
        height_terms: list[float] = []
        pose_terms: list[float] = []
        heights = [max(sample.bbox_height_px, 1.0) for sample in samples]
        median_height = float(np.median(np.asarray(heights, dtype=np.float64)))
        for sample in samples:
            height_terms.append(
                1.0
                - min(abs(sample.bbox_height_px - median_height) / median_height, 1.0)
            )
            if sample.pose_ankle_pixel is None or sample.pose_head_pixel is None:
                continue
            ankle_error = (
                (sample.pose_ankle_pixel[0] - sample.bbox_bottom[0]) ** 2
                + (sample.pose_ankle_pixel[1] - sample.bbox_bottom[1]) ** 2
            ) ** 0.5
            head_error = (
                (sample.pose_head_pixel[0] - sample.bbox_top[0]) ** 2
                + (sample.pose_head_pixel[1] - sample.bbox_top[1]) ** 2
            ) ** 0.5
            pose_terms.append(1.0 - min((ankle_error + head_error) / median_height, 1.0))
        score = float(np.mean(np.asarray(height_terms, dtype=np.float64)))
        if pose_terms:
            score = min(1.0, score + 0.15 * float(np.mean(pose_terms)))
        else:
            score = min(score, 0.85)
        return max(0.0, min(1.0, score))

    @staticmethod
    def _recommended_scale_factor(
        speeds: np.ndarray,
        scales: np.ndarray,
    ) -> float | None:
        order = np.argsort(scales)
        bucket_size = max(1, speeds.size // 3)
        near_speed = max(float(np.mean(speeds[order[:bucket_size]])), 1e-6)
        far_speed = max(float(np.mean(speeds[order[-bucket_size:]])), 1e-6)
        factor = near_speed / far_speed
        return float(max(0.05, min(1.0, factor)))
