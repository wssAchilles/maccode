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
    inlier_count: int
    condition_number: float
    inlier_mask: list[bool]
    calibration_quality: str
