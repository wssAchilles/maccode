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
