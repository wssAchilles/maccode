from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True)
class CalibrationPoint:
    pixel_x: float
    pixel_y: float
    world_x: float
    world_y: float

    @property
    def pixel(self) -> tuple[float, float]:
        return (self.pixel_x, self.pixel_y)

    @property
    def world(self) -> tuple[float, float]:
        return (self.world_x, self.world_y)


@dataclass(frozen=True)
class CalibrationConfig:
    points: list[CalibrationPoint]

    @property
    def is_valid(self) -> bool:
        return len(self.points) >= 4


@dataclass(frozen=True)
class HomographyResult:
    homography_matrix: NDArray[np.float64]
    reprojection_rmse: float
    pixel_to_world_rmse_m: float
    world_to_pixel_rmse_px: float
    inlier_count: int
    condition_number: float
    inlier_mask: list[bool]
    calibration_quality: str
    refinement_applied: bool = False
    refinement_initial_rmse_m: float | None = None
    refinement_final_rmse_m: float | None = None
    refinement_iterations: int | None = None
    runtime_homography_source: str = "planar_homography"


@dataclass(frozen=True)
class MetricPlaneCalibration:
    plane_id: str
    plane_kind: str
    pixel_polygon: list[tuple[float, float]]
    world_polygon: list[tuple[float, float]]
    control_points: list[CalibrationPoint]
    validation_segments: list[dict[str, object]]
    homography: HomographyResult
    trusted: bool

    def contains_pixel(self, pixel: tuple[float, float]) -> bool:
        return self._point_in_polygon(pixel, self.pixel_polygon)

    def to_diagnostics(self) -> dict[str, object]:
        return {
            "plane_id": self.plane_id,
            "plane_kind": self.plane_kind,
            "trusted": self.trusted,
            "control_point_count": len(self.control_points),
            "validation_segment_count": len(self.validation_segments),
            "pixel_polygon": [[x, y] for x, y in self.pixel_polygon],
            "world_polygon": [[x, y] for x, y in self.world_polygon],
            "pixel_to_world_rmse_m": self.homography.pixel_to_world_rmse_m,
            "world_to_pixel_rmse_px": self.homography.world_to_pixel_rmse_px,
            "condition_number": self.homography.condition_number,
            "calibration_quality": self.homography.calibration_quality,
            "runtime_homography_source": self.homography.runtime_homography_source,
        }

    @staticmethod
    def _point_in_polygon(
        point: tuple[float, float],
        polygon: list[tuple[float, float]],
    ) -> bool:
        if len(polygon) < 3:
            return False
        x, y = point
        inside = False
        previous_x, previous_y = polygon[-1]
        for current_x, current_y in polygon:
            crosses = (current_y > y) != (previous_y > y)
            if crosses:
                denominator = previous_y - current_y
                if abs(denominator) <= 1e-12:
                    previous_x, previous_y = current_x, current_y
                    continue
                intersection_x = (
                    (previous_x - current_x) * (y - current_y) / denominator
                    + current_x
                )
                if x < intersection_x:
                    inside = not inside
            previous_x, previous_y = current_x, current_y
        return inside


@dataclass(frozen=True)
class MetricPlaneSelection:
    plane: MetricPlaneCalibration | None
    status: str
    reason: str | None


@dataclass(frozen=True)
class MetricPlaneSet:
    planes: list[MetricPlaneCalibration]
    default_plane_id: str = "road"
    allow_default_fallback: bool = True

    def select(self, pixel: tuple[float, float]) -> MetricPlaneSelection:
        matches = [plane for plane in self.planes if plane.contains_pixel(pixel)]
        trusted_matches = [plane for plane in matches if plane.trusted]
        if len(trusted_matches) == 1:
            return MetricPlaneSelection(trusted_matches[0], "selected", None)
        if len(trusted_matches) > 1:
            return MetricPlaneSelection(
                None,
                "ambiguous",
                "plane_transition_geometry_invalid",
            )
        if matches:
            return MetricPlaneSelection(None, "untrusted", "metric_plane_not_trusted")
        default_plane = self.default_plane
        if self.allow_default_fallback and default_plane is not None and default_plane.trusted:
            return MetricPlaneSelection(default_plane, "default", None)
        return MetricPlaneSelection(None, "unresolved", "plane_unresolved")

    @property
    def default_plane(self) -> MetricPlaneCalibration | None:
        for plane in self.planes:
            if plane.plane_id == self.default_plane_id:
                return plane
        return self.planes[0] if self.planes else None

    def to_diagnostics(self) -> list[dict[str, object]]:
        return [plane.to_diagnostics() for plane in self.planes]


@dataclass(frozen=True)
class HomographyGridLine:
    kind: str
    world_start: tuple[float, float]
    world_end: tuple[float, float]
    pixel_start: tuple[float, float]
    pixel_end: tuple[float, float]

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "world_start": list(self.world_start),
            "world_end": list(self.world_end),
            "pixel_start": list(self.pixel_start),
            "pixel_end": list(self.pixel_end),
        }


@dataclass(frozen=True)
class HomographyGrid:
    frame_width: int
    frame_height: int
    spacing_m: float
    world_width_m: float
    world_length_m: float
    generated_from: str
    calibration_source: str
    calibration_trusted: bool
    pixel_rmse_px: float
    world_rmse_m: float
    validation_max_error_px: float | None
    road_plane_polygon_world: list[tuple[float, float]] | None
    lines: list[HomographyGridLine]

    def to_dict(self) -> dict[str, object]:
        return {
            "frame_width": self.frame_width,
            "frame_height": self.frame_height,
            "spacing_m": self.spacing_m,
            "world_width_m": self.world_width_m,
            "world_length_m": self.world_length_m,
            "generated_from": self.generated_from,
            "calibration_source": self.calibration_source,
            "calibration_trusted": self.calibration_trusted,
            "pixel_rmse_px": self.pixel_rmse_px,
            "world_rmse_m": self.world_rmse_m,
            "validation_max_error_px": self.validation_max_error_px,
            "road_plane_polygon_world": [
                list(point) for point in self.road_plane_polygon_world
            ]
            if self.road_plane_polygon_world is not None
            else None,
            "lines": [line.to_dict() for line in self.lines],
        }
