from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from domain.calibration.models import CalibrationPoint, MetricPlaneCalibration
from domain.calibration.service import CalibrationService
from domain.speed.view_transformer import ViewTransformer

PEDESTRIAN_PLANE_KINDS = {"sidewalk", "curb", "plaza", "person_corridor"}


@dataclass(frozen=True)
class PointGeometryPosterior:
    plane_id: str
    pixel: tuple[float, float]
    homography_std_m: float | None
    jacobian_amplification: float | None
    extrapolation_risk: str
    gate_reason: str | None

    def to_diagnostics(self) -> dict[str, object]:
        return {
            "plane_id": self.plane_id,
            "pixel": [float(self.pixel[0]), float(self.pixel[1])],
            "point_homography_std_m": self.homography_std_m,
            "point_jacobian_amplification": self.jacobian_amplification,
            "point_extrapolation_risk": self.extrapolation_risk,
            "point_metric_gate_reason": self.gate_reason,
            "model_reference": "point_metric_geometry_posterior_v6",
        }


@dataclass(frozen=True)
class PlaneGeometryPosterior:
    plane_id: str
    plane_kind: str
    trusted: bool
    homography_samples: list[list[list[float]]]
    homography_sample_std_m: float | None
    scale_anchor_uncertainty_m: float | None
    plane_posterior_covariance: list[list[float]] | None
    jacobian_amplification_map: list[dict[str, float]]
    jacobian_amplification_p95: float | None
    extrapolation_zone: str
    gate_reason: str | None

    def to_diagnostics(self) -> dict[str, object]:
        return {
            "plane_id": self.plane_id,
            "plane_kind": self.plane_kind,
            "trusted": self.trusted,
            "homography_samples": self.homography_samples,
            "homography_sample_std_m": self.homography_sample_std_m,
            "scale_anchor_uncertainty_m": self.scale_anchor_uncertainty_m,
            "plane_posterior_covariance": self.plane_posterior_covariance,
            "jacobian_amplification_map": self.jacobian_amplification_map,
            "jacobian_amplification_p95": self.jacobian_amplification_p95,
            "extrapolation_zone": self.extrapolation_zone,
            "gate_reason": self.gate_reason,
            "model_reference": "metric_plane_geometry_posterior_v5",
        }


@dataclass(frozen=True)
class MetricGeometryPosterior:
    planes: dict[str, PlaneGeometryPosterior]
    source_planes: dict[str, MetricPlaneCalibration]
    homography_posterior_gate_reason: str | None
    scale_anchor_summary: dict[str, object]
    jacobian_amplification_map_summary: dict[str, object]
    model_reference: str = "metric_geometry_posterior_v5"

    def plane(self, plane_id: str | None) -> PlaneGeometryPosterior | None:
        if plane_id is None:
            return None
        return self.planes.get(plane_id)

    def evaluate_point(
        self,
        plane_id: str | None,
        pixel: tuple[float, float],
    ) -> PointGeometryPosterior | None:
        plane_posterior = self.plane(plane_id)
        plane = self.source_planes.get(plane_id or "")
        if plane_posterior is None or plane is None:
            return None
        sample_std = _point_sample_world_std(pixel, plane_posterior.homography_samples)
        amplification = _point_jacobian_amplification(plane, pixel)
        extrapolation_risk = (
            "inside_metric_plane"
            if plane.contains_pixel(pixel)
            else "outside_metric_plane_support"
        )
        gate_reason = self._point_gate_reason(
            plane_posterior,
            homography_std_m=sample_std,
            jacobian_amplification=amplification,
            extrapolation_risk=extrapolation_risk,
        )
        return PointGeometryPosterior(
            plane_id=plane.plane_id,
            pixel=pixel,
            homography_std_m=sample_std,
            jacobian_amplification=amplification,
            extrapolation_risk=extrapolation_risk,
            gate_reason=gate_reason,
        )

    @staticmethod
    def _point_gate_reason(
        plane_posterior: PlaneGeometryPosterior,
        *,
        homography_std_m: float | None,
        jacobian_amplification: float | None,
        extrapolation_risk: str,
    ) -> str | None:
        if plane_posterior.gate_reason is not None:
            return plane_posterior.gate_reason
        if extrapolation_risk == "outside_metric_plane_support":
            return "outside_metric_plane_support"
        if homography_std_m is not None and homography_std_m > 0.75:
            return "homography_posterior_too_wide"
        if jacobian_amplification is not None and jacobian_amplification > 0.35:
            return "jacobian_amplification_high"
        return None

    def to_diagnostics(self) -> dict[str, object]:
        return {
            "planes": {
                plane_id: posterior.to_diagnostics()
                for plane_id, posterior in self.planes.items()
            },
            "homography_posterior_gate_reason": self.homography_posterior_gate_reason,
            "scale_anchor_summary": self.scale_anchor_summary,
            "jacobian_amplification_map_summary": self.jacobian_amplification_map_summary,
            "model_reference": self.model_reference,
        }


class MetricGeometryPosteriorBuilder:
    def build(
        self,
        planes: list[MetricPlaneCalibration],
        *,
        frame_width: int,
        frame_height: int,
    ) -> MetricGeometryPosterior:
        plane_posteriors = {
            plane.plane_id: self._plane_posterior(
                plane,
                frame_width=frame_width,
                frame_height=frame_height,
            )
            for plane in planes
        }
        gate_reasons = sorted(
            {
                posterior.gate_reason
                for posterior in plane_posteriors.values()
                if posterior.gate_reason is not None
            },
        )
        scale_values = [
            posterior.scale_anchor_uncertainty_m
            for posterior in plane_posteriors.values()
            if posterior.scale_anchor_uncertainty_m is not None
        ]
        jacobian_values = [
            posterior.jacobian_amplification_p95
            for posterior in plane_posteriors.values()
            if posterior.jacobian_amplification_p95 is not None
        ]
        return MetricGeometryPosterior(
            planes=plane_posteriors,
            source_planes={plane.plane_id: plane for plane in planes},
            homography_posterior_gate_reason=gate_reasons[0] if gate_reasons else None,
            scale_anchor_summary={
                "plane_count": len(plane_posteriors),
                "max_scale_anchor_uncertainty_m": max(scale_values)
                if scale_values
                else None,
                "missing_scale_anchor_count": sum(
                    1
                    for posterior in plane_posteriors.values()
                    if posterior.scale_anchor_uncertainty_m is None
                ),
            },
            jacobian_amplification_map_summary={
                "max_jacobian_amplification_p95": max(jacobian_values)
                if jacobian_values
                else None,
                "high_amplification_plane_count": sum(
                    1
                    for posterior in plane_posteriors.values()
                    if (posterior.jacobian_amplification_p95 or 0.0) > 0.25
                ),
            },
        )

    def _plane_posterior(
        self,
        plane: MetricPlaneCalibration,
        *,
        frame_width: int,
        frame_height: int,
    ) -> PlaneGeometryPosterior:
        samples = self._sample_homographies(plane)
        sample_std = self._sample_world_std(plane, samples)
        scale_uncertainty = self._scale_anchor_uncertainty(plane)
        jacobian_map, jacobian_p95 = self._jacobian_map(plane, frame_width, frame_height)
        covariance = (
            [[sample_std**2, 0.0], [0.0, sample_std**2]]
            if sample_std is not None
            else None
        )
        extrapolation_zone = "inside_metric_plane" if plane.pixel_polygon else "unknown"
        gate_reason = self._gate_reason(
            plane,
            homography_sample_std_m=sample_std,
            scale_anchor_uncertainty_m=scale_uncertainty,
            jacobian_amplification_p95=jacobian_p95,
        )
        return PlaneGeometryPosterior(
            plane_id=plane.plane_id,
            plane_kind=plane.plane_kind,
            trusted=plane.trusted,
            homography_samples=[
                np.asarray(sample, dtype=float).round(8).tolist() for sample in samples
            ],
            homography_sample_std_m=sample_std,
            scale_anchor_uncertainty_m=scale_uncertainty,
            plane_posterior_covariance=covariance,
            jacobian_amplification_map=jacobian_map,
            jacobian_amplification_p95=jacobian_p95,
            extrapolation_zone=extrapolation_zone,
            gate_reason=gate_reason,
        )

    @staticmethod
    def _sample_homographies(plane: MetricPlaneCalibration) -> list[np.ndarray]:
        points = plane.control_points
        if len(points) < 4:
            return []
        pixel_noise = max(plane.homography.world_to_pixel_rmse_px, 1.0)
        offsets = [
            (0.0, 0.0),
            (pixel_noise, 0.0),
            (-pixel_noise, 0.0),
            (0.0, pixel_noise),
            (0.0, -pixel_noise),
        ]
        samples: list[np.ndarray] = []
        service = CalibrationService()
        for dx, dy in offsets:
            jittered = [
                CalibrationPoint(
                    pixel_x=point.pixel_x + dx,
                    pixel_y=point.pixel_y + dy,
                    world_x=point.world_x,
                    world_y=point.world_y,
                )
                for point in points
            ]
            try:
                samples.append(service.compute_homography(jittered).homography_matrix)
            except ValueError:
                continue
        return samples or [plane.homography.homography_matrix]

    @staticmethod
    def _sample_world_std(
        plane: MetricPlaneCalibration,
        samples: list[np.ndarray],
    ) -> float | None:
        if len(samples) < 2:
            return None
        polygon = plane.pixel_polygon or [point.pixel for point in plane.control_points[:4]]
        centroid = (
            sum(point[0] for point in polygon) / len(polygon),
            sum(point[1] for point in polygon) / len(polygon),
        )
        worlds: list[tuple[float, float]] = []
        for matrix in samples:
            worlds.append(ViewTransformer(matrix).transform_point(*centroid))
        mean_x = sum(point[0] for point in worlds) / len(worlds)
        mean_y = sum(point[1] for point in worlds) / len(worlds)
        residuals = [math.dist(point, (mean_x, mean_y)) for point in worlds]
        return float(np.percentile(residuals, 95))

    @staticmethod
    def _scale_anchor_uncertainty(plane: MetricPlaneCalibration) -> float | None:
        values: list[float] = [plane.homography.pixel_to_world_rmse_m]
        for segment in plane.validation_segments:
            value = segment.get("length_error_m") if isinstance(segment, dict) else None
            if isinstance(value, int | float):
                values.append(abs(float(value)))
        if not values:
            return None
        return float(max(values))

    @staticmethod
    def _jacobian_map(
        plane: MetricPlaneCalibration,
        frame_width: int,
        frame_height: int,
    ) -> tuple[list[dict[str, float]], float | None]:
        transformer = ViewTransformer(plane.homography.homography_matrix)
        polygon = plane.pixel_polygon or [
            (0.15 * frame_width, 0.15 * frame_height),
            (0.85 * frame_width, 0.15 * frame_height),
            (0.85 * frame_width, 0.85 * frame_height),
            (0.15 * frame_width, 0.85 * frame_height),
        ]
        xs = [point[0] for point in polygon]
        ys = [point[1] for point in polygon]
        sample_points = [
            (sum(xs) / len(xs), sum(ys) / len(ys)),
            (min(xs), min(ys)),
            (max(xs), min(ys)),
            (max(xs), max(ys)),
            (min(xs), max(ys)),
        ]
        rows: list[dict[str, float]] = []
        values: list[float] = []
        for x, y in sample_points:
            jacobian = transformer.local_jacobian(float(x), float(y))
            singular_values = np.linalg.svd(jacobian, compute_uv=False)
            amplification = float(max(singular_values))
            values.append(amplification)
            rows.append({"pixel_x": float(x), "pixel_y": float(y), "amplification": amplification})
        return rows, float(np.percentile(values, 95)) if values else None

    @staticmethod
    def _gate_reason(
        plane: MetricPlaneCalibration,
        *,
        homography_sample_std_m: float | None,
        scale_anchor_uncertainty_m: float | None,
        jacobian_amplification_p95: float | None,
    ) -> str | None:
        if not plane.trusted:
            return "metric_plane_not_trusted"
        if scale_anchor_uncertainty_m is None:
            return "scale_anchor_missing"
        if scale_anchor_uncertainty_m > 0.75:
            return "scale_anchor_untrusted"
        if homography_sample_std_m is not None and homography_sample_std_m > 0.75:
            return "homography_posterior_too_wide"
        if jacobian_amplification_p95 is not None and jacobian_amplification_p95 > 0.35:
            return "jacobian_amplification_high"
        return None


def _point_sample_world_std(
    pixel: tuple[float, float],
    homography_samples: list[list[list[float]]],
) -> float | None:
    if len(homography_samples) < 2:
        return None
    worlds: list[tuple[float, float]] = []
    for matrix in homography_samples:
        worlds.append(ViewTransformer(np.asarray(matrix, dtype=float)).transform_point(*pixel))
    mean_x = sum(point[0] for point in worlds) / len(worlds)
    mean_y = sum(point[1] for point in worlds) / len(worlds)
    residuals = [math.dist(point, (mean_x, mean_y)) for point in worlds]
    return float(np.percentile(residuals, 95))


def _point_jacobian_amplification(
    plane: MetricPlaneCalibration,
    pixel: tuple[float, float],
) -> float | None:
    transformer = ViewTransformer(plane.homography.homography_matrix)
    try:
        singular_values = np.linalg.svd(transformer.local_jacobian(*pixel), compute_uv=False)
    except ValueError:
        return None
    return float(max(singular_values))
