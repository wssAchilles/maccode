from __future__ import annotations

import math
import random

import numpy as np
from numpy.typing import NDArray

from domain.calibration.models import CalibrationPoint, HomographyResult


class CalibrationService:
    def validate_points(self, points: list[CalibrationPoint]) -> bool:
        if len(points) < 4:
            raise ValueError("homography calibration requires at least 4 points")
        pixel_points = np.array([point.pixel for point in points], dtype=float)
        world_points = np.array([point.world for point in points], dtype=float)
        if self._is_collinear(pixel_points) or self._is_collinear(world_points):
            raise ValueError("calibration points must not be collinear")
        return True

    def compute_homography(self, points: list[CalibrationPoint]) -> HomographyResult:
        self.validate_points(points)
        pixel_points = np.array([point.pixel for point in points], dtype=float)
        world_points = np.array([point.world for point in points], dtype=float)
        matrix, condition_number = self._solve_dlt(pixel_points, world_points)
        rmse = self.compute_reprojection_error(matrix, pixel_points, world_points)
        return HomographyResult(
            homography_matrix=matrix,
            reprojection_rmse=rmse,
            inlier_count=len(points),
            condition_number=condition_number,
            inlier_mask=[True] * len(points),
            calibration_quality=self._classify_quality(rmse, condition_number, len(points)),
        )

    def compute_homography_ransac(
        self,
        points: list[CalibrationPoint],
        reprojection_threshold: float = 0.5,
        max_iterations: int = 300,
        random_seed: int | None = None,
    ) -> HomographyResult:
        self.validate_points(points)
        if reprojection_threshold <= 0:
            raise ValueError("reprojection_threshold must be positive")
        if max_iterations <= 0:
            raise ValueError("max_iterations must be positive")

        pixel_points = np.array([point.pixel for point in points], dtype=float)
        world_points = np.array([point.world for point in points], dtype=float)
        sampler = random.Random(random_seed)
        best_mask: NDArray[np.bool_] | None = None
        best_rmse = float("inf")
        best_inlier_count = 0

        for _ in range(max_iterations):
            sample_indices = sampler.sample(range(len(points)), 4)
            sample_pixels = pixel_points[sample_indices]
            sample_world = world_points[sample_indices]
            if self._is_collinear(sample_pixels) or self._is_collinear(sample_world):
                continue
            try:
                candidate_matrix, _ = self._solve_dlt(sample_pixels, sample_world)
            except np.linalg.LinAlgError:
                continue

            projected = self._project_points(candidate_matrix, pixel_points)
            errors = np.linalg.norm(projected - world_points, axis=1)
            mask = errors <= reprojection_threshold
            inlier_count = int(mask.sum())
            if inlier_count < 4:
                continue
            inlier_rmse = float(math.sqrt(np.mean(errors[mask] ** 2)))
            if inlier_count > best_inlier_count or (
                inlier_count == best_inlier_count and inlier_rmse < best_rmse
            ):
                best_mask = mask
                best_rmse = inlier_rmse
                best_inlier_count = inlier_count

        if best_mask is None:
            return self.compute_homography(points)

        inlier_pixels = pixel_points[best_mask]
        inlier_world = world_points[best_mask]
        matrix, condition_number = self._solve_dlt(inlier_pixels, inlier_world)
        rmse = self.compute_reprojection_error(matrix, inlier_pixels, inlier_world)
        return HomographyResult(
            homography_matrix=matrix,
            reprojection_rmse=rmse,
            inlier_count=best_inlier_count,
            condition_number=condition_number,
            inlier_mask=[bool(value) for value in best_mask.tolist()],
            calibration_quality=self._classify_quality(rmse, condition_number, best_inlier_count),
        )

    def compute_reprojection_error(
        self,
        homography_matrix: NDArray[np.float64],
        pixel_points: NDArray[np.float64],
        world_points: NDArray[np.float64],
    ) -> float:
        projected = self._project_points(homography_matrix, pixel_points)
        errors = np.linalg.norm(projected - world_points, axis=1)
        return float(math.sqrt(np.mean(errors**2)))

    @staticmethod
    def _is_collinear(points: NDArray[np.float64]) -> bool:
        centered = points - np.mean(points, axis=0)
        return bool(np.linalg.matrix_rank(centered, tol=1e-9) < 2)

    @staticmethod
    def _solve_dlt(
        pixel_points: NDArray[np.float64],
        world_points: NDArray[np.float64],
    ) -> tuple[NDArray[np.float64], float]:
        rows: list[list[float]] = []
        for (u, v), (x, y) in zip(pixel_points, world_points, strict=True):
            rows.append([u, v, 1.0, 0.0, 0.0, 0.0, -u * x, -v * x, -x])
            rows.append([0.0, 0.0, 0.0, u, v, 1.0, -u * y, -v * y, -y])
        a = np.array(rows, dtype=float)
        _, singular_values, vh = np.linalg.svd(a)
        h = vh[-1].reshape(3, 3)
        if abs(h[2, 2]) > 1e-12:
            h = h / h[2, 2]
        condition_number = float(singular_values[0] / singular_values[-1])
        return h.astype(np.float64), condition_number

    @staticmethod
    def _project_points(
        homography_matrix: NDArray[np.float64],
        pixel_points: NDArray[np.float64],
    ) -> NDArray[np.float64]:
        ones = np.ones((pixel_points.shape[0], 1), dtype=float)
        homogeneous = np.hstack([pixel_points, ones])
        projected = homogeneous @ homography_matrix.T
        projected = projected / projected[:, 2:3]
        return projected[:, :2]

    @staticmethod
    def _classify_quality(rmse: float, condition_number: float, inlier_count: int) -> str:
        if inlier_count < 4 or not math.isfinite(condition_number):
            return "unstable"
        if rmse <= 0.5:
            return "excellent"
        if rmse <= 2.0:
            return "usable"
        return "unstable"
