from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class PedestrianTrackSample:
    timestamp_sec: float
    foot_pixel: tuple[float, float]
    head_pixel: tuple[float, float] | None = None


@dataclass(frozen=True)
class PedestrianCalibrationCandidate:
    walking_vp_pixel: tuple[float, float] | None
    vertical_vp_pixel: tuple[float, float] | None
    sidewalk_plane_polygon: list[tuple[float, float]]
    scale_hypothesis: dict[str, float]
    shoe_trace_line_residual_px: float | None
    foot_periodicity_score: float
    head_foot_vertical_consistency: float
    bev_path_straightness: float
    speed_local_scale_correlation_after_projection: float | None
    quality_score: float
    trusted: bool
    rejection_reason: str | None


class PedestrianCalibrationCandidateBuilder:
    """Generate an untrusted pedestrian-plane calibration candidate from foot traces."""

    def build(
        self,
        samples: list[PedestrianTrackSample],
        *,
        validation_segments: list[dict[str, object]] | None = None,
    ) -> PedestrianCalibrationCandidate:
        if len(samples) < 6:
            return self._rejected("insufficient_pedestrian_track_samples")
        foot_points = np.asarray([sample.foot_pixel for sample in samples], dtype=np.float64)
        if not np.all(np.isfinite(foot_points)):
            return self._rejected("invalid_pedestrian_track_samples")
        centroid = foot_points.mean(axis=0)
        centered = foot_points - centroid
        _, singular_values, right_t = np.linalg.svd(centered, full_matrices=False)
        direction = right_t[0]
        if direction[0] < 0:
            direction = -direction
        trace_extent = float(singular_values[0] / max(len(samples) ** 0.5, 1.0))
        if trace_extent <= 1e-6:
            return self._rejected("pedestrian_trace_quality_gate_failed")
        residuals = np.abs(centered @ np.array([-direction[1], direction[0]]))
        shoe_residual = float(np.sqrt(np.mean(residuals**2)))
        straightness = float(max(0.0, 1.0 - shoe_residual / max(trace_extent, 1.0)))
        periodicity = self._periodicity_score(foot_points, direction)
        vertical_consistency = self._head_foot_vertical_consistency(samples)
        quality = float(
            0.40 * straightness
            + 0.30 * periodicity
            + 0.30 * vertical_consistency
        )
        vp_distance = max(500.0, trace_extent * 40.0)
        walking_vp = (
            float(centroid[0] + direction[0] * vp_distance),
            float(centroid[1] + direction[1] * vp_distance),
        )
        vertical_vp = self._vertical_vp(samples)
        polygon = self._trace_polygon(foot_points, direction)
        has_validation = bool(validation_segments)
        trusted = bool(quality >= 0.80 and has_validation)
        rejection_reason = None
        if not trusted:
            rejection_reason = (
                "requires_metric_validation_segments"
                if quality >= 0.65
                else "pedestrian_trace_quality_gate_failed"
            )
        return PedestrianCalibrationCandidate(
            walking_vp_pixel=walking_vp,
            vertical_vp_pixel=vertical_vp,
            sidewalk_plane_polygon=polygon,
            scale_hypothesis={
                "nominal_pedestrian_height_m": 1.70,
                "nominal_step_length_m": 0.72,
            },
            shoe_trace_line_residual_px=shoe_residual,
            foot_periodicity_score=periodicity,
            head_foot_vertical_consistency=vertical_consistency,
            bev_path_straightness=straightness,
            speed_local_scale_correlation_after_projection=None,
            quality_score=quality,
            trusted=trusted,
            rejection_reason=rejection_reason,
        )

    @staticmethod
    def _periodicity_score(points: np.ndarray, direction: np.ndarray) -> float:
        projected = points @ direction
        steps = np.diff(projected)
        if len(steps) < 5:
            return 0.0
        centered_steps = steps - float(np.mean(steps))
        alternating = np.array([1.0 if index % 2 == 0 else -1.0 for index in range(len(steps))])
        denominator = float(np.linalg.norm(centered_steps) * np.linalg.norm(alternating))
        if denominator <= 1e-9:
            return 0.65
        correlation = abs(float(centered_steps @ alternating) / denominator)
        step_cv = float(np.std(np.abs(steps)) / max(float(np.mean(np.abs(steps))), 1e-9))
        regularity = max(0.0, 1.0 - step_cv)
        return float(max(correlation, regularity * 0.65))

    @staticmethod
    def _head_foot_vertical_consistency(samples: list[PedestrianTrackSample]) -> float:
        vectors = [
            (
                float(sample.head_pixel[0] - sample.foot_pixel[0]),
                float(sample.head_pixel[1] - sample.foot_pixel[1]),
            )
            for sample in samples
            if sample.head_pixel is not None
        ]
        if len(vectors) < 3:
            return 0.45
        angles = [math.atan2(vector[1], vector[0]) for vector in vectors]
        mean_sin = float(np.mean(np.sin(angles)))
        mean_cos = float(np.mean(np.cos(angles)))
        circular_variance = 1.0 - math.hypot(mean_sin, mean_cos)
        lengths = [math.hypot(*vector) for vector in vectors]
        length_cv = float(np.std(lengths) / max(float(np.mean(lengths)), 1e-9))
        return float(max(0.0, 1.0 - circular_variance - min(length_cv, 1.0) * 0.5))

    @staticmethod
    def _vertical_vp(samples: list[PedestrianTrackSample]) -> tuple[float, float] | None:
        vectors = [
            (
                sample.foot_pixel,
                sample.head_pixel,
            )
            for sample in samples
            if sample.head_pixel is not None
        ]
        if not vectors:
            return None
        foot = np.asarray([pair[0] for pair in vectors], dtype=np.float64).mean(axis=0)
        head = np.asarray([pair[1] for pair in vectors], dtype=np.float64).mean(axis=0)
        direction = head - foot
        norm = float(np.linalg.norm(direction))
        if norm <= 1e-9:
            return None
        direction /= norm
        return (float(foot[0] + direction[0] * 500.0), float(foot[1] + direction[1] * 500.0))

    @staticmethod
    def _trace_polygon(points: np.ndarray, direction: np.ndarray) -> list[tuple[float, float]]:
        normal = np.array([-direction[1], direction[0]], dtype=np.float64)
        projected = points @ direction
        min_point = points[int(np.argmin(projected))]
        max_point = points[int(np.argmax(projected))]
        width_px = max(12.0, float(np.std(points @ normal)) * 4.0)
        corners = [
            min_point - normal * width_px,
            max_point - normal * width_px,
            max_point + normal * width_px,
            min_point + normal * width_px,
        ]
        return [(float(point[0]), float(point[1])) for point in corners]

    @staticmethod
    def _rejected(reason: str) -> PedestrianCalibrationCandidate:
        return PedestrianCalibrationCandidate(
            walking_vp_pixel=None,
            vertical_vp_pixel=None,
            sidewalk_plane_polygon=[],
            scale_hypothesis={},
            shoe_trace_line_residual_px=None,
            foot_periodicity_score=0.0,
            head_foot_vertical_consistency=0.0,
            bev_path_straightness=0.0,
            speed_local_scale_correlation_after_projection=None,
            quality_score=0.0,
            trusted=False,
            rejection_reason=reason,
        )
