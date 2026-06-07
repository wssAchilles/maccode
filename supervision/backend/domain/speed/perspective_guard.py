from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class PerspectiveGuardSample:
    speed_kmh: float
    pixel_y: float
    local_scale_factor: float
    local_scale_percentile: float
    timestamp_sec: float


@dataclass(frozen=True)
class PerspectiveGuardResult:
    perspective_speed_inflation_detected: bool
    speed_scale_correlation: float | None
    far_near_speed_ratio: float | None
    geometry_rejection_reason: str | None
    model_reference: str = "pedestrian_perspective_speed_guard_v1"

    def to_dict(self) -> dict[str, object]:
        return {
            "perspective_speed_inflation_detected": (
                self.perspective_speed_inflation_detected
            ),
            "speed_scale_correlation": self.speed_scale_correlation,
            "far_near_speed_ratio": self.far_near_speed_ratio,
            "geometry_rejection_reason": self.geometry_rejection_reason,
            "model_reference": self.model_reference,
        }


class PerspectiveSpeedInflationDetector:
    def __init__(
        self,
        *,
        min_sample_count: int = 5,
        far_near_ratio_threshold: float = 2.0,
        far_speed_threshold_kmh: float = 12.0,
        correlation_threshold: float = 0.65,
        far_scale_percentile_threshold: float = 0.85,
        direct_reject_percentile: float = 0.95,
    ) -> None:
        self.min_sample_count = min_sample_count
        self.far_near_ratio_threshold = far_near_ratio_threshold
        self.far_speed_threshold_kmh = far_speed_threshold_kmh
        self.correlation_threshold = correlation_threshold
        self.far_scale_percentile_threshold = far_scale_percentile_threshold
        self.direct_reject_percentile = direct_reject_percentile

    def analyze(
        self,
        samples: list[PerspectiveGuardSample],
        *,
        max_speed_kmh: float,
    ) -> PerspectiveGuardResult:
        if len(samples) < self.min_sample_count:
            return PerspectiveGuardResult(False, None, None, None)

        ordered = sorted(samples, key=lambda sample: sample.timestamp_sec)
        speeds = np.asarray([sample.speed_kmh for sample in ordered], dtype=np.float64)
        scales = np.asarray([sample.local_scale_factor for sample in ordered], dtype=np.float64)
        percentiles = np.asarray(
            [sample.local_scale_percentile for sample in ordered],
            dtype=np.float64,
        )
        correlation = self._correlation(speeds, scales)
        far_near_ratio = self._far_near_speed_ratio(speeds, scales)
        far_mask = percentiles >= self.far_scale_percentile_threshold
        far_speed = (
            float(np.max(speeds[far_mask]))
            if np.any(far_mask)
            else float(np.max(speeds))
        )
        max_percentile = float(np.max(percentiles))
        max_speed = float(np.max(speeds))

        detected = False
        if max_percentile >= self.direct_reject_percentile and max_speed > max_speed_kmh:
            detected = True
        if (
            far_near_ratio is not None
            and far_near_ratio >= self.far_near_ratio_threshold
            and far_speed > self.far_speed_threshold_kmh
        ):
            detected = True
        if (
            correlation is not None
            and correlation >= self.correlation_threshold
            and max_percentile >= self.far_scale_percentile_threshold
        ):
            detected = True

        return PerspectiveGuardResult(
            perspective_speed_inflation_detected=detected,
            speed_scale_correlation=correlation,
            far_near_speed_ratio=far_near_ratio,
            geometry_rejection_reason=(
                "perspective_speed_inflation" if detected else None
            ),
        )

    @staticmethod
    def _correlation(
        speeds: np.ndarray,
        scales: np.ndarray,
    ) -> float | None:
        if speeds.size < 2 or float(np.std(speeds)) <= 1e-9 or float(np.std(scales)) <= 1e-9:
            return None
        return float(np.corrcoef(speeds, scales)[0, 1])

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
        near_mean = max(float(np.mean(near)), 1e-6)
        return float(np.mean(far) / near_mean)
