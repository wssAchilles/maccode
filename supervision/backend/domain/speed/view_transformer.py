from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


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
