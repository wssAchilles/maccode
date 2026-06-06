from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True)
class LocalPositionUncertainty:
    covariance: NDArray[np.float64]
    position_sigma_m: float
    local_scale_factor: float


class ViewTransformer:
    def __init__(self, homography_matrix: NDArray[np.float64]) -> None:
        matrix = np.asarray(homography_matrix, dtype=float)
        if matrix.shape != (3, 3):
            raise ValueError("homography_matrix must have shape (3, 3)")
        self.homography_matrix = matrix

    def transform_point(self, pixel_x: float, pixel_y: float) -> tuple[float, float]:
        points = self.transform_points(np.array([[pixel_x, pixel_y]], dtype=float))
        return (float(points[0, 0]), float(points[0, 1]))

    def transform_points(self, pixel_points: NDArray[np.float64]) -> NDArray[np.float64]:
        points = np.asarray(pixel_points, dtype=float)
        if points.ndim != 2 or points.shape[1] != 2:
            raise ValueError("pixel_points must have shape (N, 2)")
        ones = np.ones((points.shape[0], 1), dtype=float)
        homogeneous = np.hstack([points, ones])
        projected = homogeneous @ self.homography_matrix.T
        projected = projected / projected[:, 2:3]
        return projected[:, :2].astype(np.float64)

    def local_position_uncertainty(
        self,
        pixel_x: float,
        pixel_y: float,
        pixel_sigma: float = 1.0,
    ) -> LocalPositionUncertainty:
        if pixel_sigma < 0:
            raise ValueError("pixel_sigma must not be negative")
        jacobian = self.local_jacobian(pixel_x, pixel_y)
        pixel_covariance = np.eye(2, dtype=np.float64) * (pixel_sigma**2)
        covariance = jacobian @ pixel_covariance @ jacobian.T
        variance = max(float(np.trace(covariance) / 2.0), 0.0)
        position_sigma_m = variance**0.5
        base_scale = max(self._base_scale(), 1e-9)
        local_scale = float(np.linalg.norm(jacobian, ord=2))
        return LocalPositionUncertainty(
            covariance=covariance.astype(np.float64),
            position_sigma_m=float(position_sigma_m),
            local_scale_factor=float(max(1.0, local_scale / base_scale)),
        )

    def local_jacobian(self, pixel_x: float, pixel_y: float) -> NDArray[np.float64]:
        h = self.homography_matrix
        denominator = h[2, 0] * pixel_x + h[2, 1] * pixel_y + h[2, 2]
        if abs(float(denominator)) <= 1e-12:
            raise ValueError("homography projection denominator is too close to zero")
        x_numerator = h[0, 0] * pixel_x + h[0, 1] * pixel_y + h[0, 2]
        y_numerator = h[1, 0] * pixel_x + h[1, 1] * pixel_y + h[1, 2]
        denominator_sq = denominator**2
        return np.array(
            [
                [
                    (h[0, 0] * denominator - x_numerator * h[2, 0]) / denominator_sq,
                    (h[0, 1] * denominator - x_numerator * h[2, 1]) / denominator_sq,
                ],
                [
                    (h[1, 0] * denominator - y_numerator * h[2, 0]) / denominator_sq,
                    (h[1, 1] * denominator - y_numerator * h[2, 1]) / denominator_sq,
                ],
            ],
            dtype=np.float64,
        )

    def _base_scale(self) -> float:
        return float(np.linalg.norm(self.local_jacobian(0.0, 0.0), ord=2))
