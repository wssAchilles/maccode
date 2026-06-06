from __future__ import annotations

import math
import random

import numpy as np
from numpy.typing import NDArray

from domain.calibration.models import (
    CalibrationPoint,
    HomographyGrid,
    HomographyGridLine,
    HomographyResult,
)


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
        matrix, refinement_applied, refinement_initial_rmse, refinement_final_rmse, iterations = (
            self._refine_homography(matrix, pixel_points, world_points)
        )
        pixel_to_world_rmse_m, world_to_pixel_rmse_px = self.compute_bidirectional_errors(
            matrix,
            pixel_points,
            world_points,
        )
        return HomographyResult(
            homography_matrix=matrix,
            reprojection_rmse=pixel_to_world_rmse_m,
            pixel_to_world_rmse_m=pixel_to_world_rmse_m,
            world_to_pixel_rmse_px=world_to_pixel_rmse_px,
            inlier_count=len(points),
            condition_number=condition_number,
            inlier_mask=[True] * len(points),
            calibration_quality=self._classify_quality(
                pixel_to_world_rmse_m,
                condition_number,
                len(points),
            ),
            refinement_applied=refinement_applied,
            refinement_initial_rmse_m=refinement_initial_rmse,
            refinement_final_rmse_m=refinement_final_rmse,
            refinement_iterations=iterations,
        )

    def compute_homography_ransac(
        self,
        points: list[CalibrationPoint],
        reprojection_threshold: float = 0.5,
        max_iterations: int = 300,
        random_seed: int | None = None,
        validation_segments: list[dict[str, object]] | None = None,
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
        validation_pixels, validation_world = self._validation_segment_points(
            validation_segments or [],
        )
        matrix, condition_number = self._solve_dlt(inlier_pixels, inlier_world)
        matrix, refinement_applied, refinement_initial_rmse, refinement_final_rmse, iterations = (
            self._refine_homography(
                matrix,
                inlier_pixels,
                inlier_world,
                validation_pixels=validation_pixels,
                validation_world=validation_world,
            )
        )
        pixel_to_world_rmse_m, world_to_pixel_rmse_px = self.compute_bidirectional_errors(
            matrix,
            inlier_pixels,
            inlier_world,
        )
        return HomographyResult(
            homography_matrix=matrix,
            reprojection_rmse=pixel_to_world_rmse_m,
            pixel_to_world_rmse_m=pixel_to_world_rmse_m,
            world_to_pixel_rmse_px=world_to_pixel_rmse_px,
            inlier_count=best_inlier_count,
            condition_number=condition_number,
            inlier_mask=[bool(value) for value in best_mask.tolist()],
            calibration_quality=self._classify_quality(
                pixel_to_world_rmse_m,
                condition_number,
                best_inlier_count,
            ),
            refinement_applied=refinement_applied,
            refinement_initial_rmse_m=refinement_initial_rmse,
            refinement_final_rmse_m=refinement_final_rmse,
            refinement_iterations=iterations,
        )

    def compute_bidirectional_errors(
        self,
        homography_matrix: NDArray[np.float64],
        pixel_points: NDArray[np.float64],
        world_points: NDArray[np.float64],
    ) -> tuple[float, float]:
        pixel_to_world_rmse_m = self.compute_reprojection_error(
            homography_matrix,
            pixel_points,
            world_points,
        )
        inverse_homography = np.linalg.inv(homography_matrix).astype(np.float64)
        projected_pixels = self._project_points(inverse_homography, world_points)
        pixel_errors = np.linalg.norm(projected_pixels - pixel_points, axis=1)
        world_to_pixel_rmse_px = float(math.sqrt(np.mean(pixel_errors**2)))
        return pixel_to_world_rmse_m, world_to_pixel_rmse_px

    def compute_reprojection_error(
        self,
        homography_matrix: NDArray[np.float64],
        pixel_points: NDArray[np.float64],
        world_points: NDArray[np.float64],
    ) -> float:
        projected = self._project_points(homography_matrix, pixel_points)
        errors = np.linalg.norm(projected - world_points, axis=1)
        return float(math.sqrt(np.mean(errors**2)))

    def build_homography_grid(
        self,
        homography: HomographyResult,
        frame_width: int,
        frame_height: int,
        world_width_m: float,
        world_length_m: float,
        spacing_m: float = 5.0,
        calibration_source: str = "manual_or_synthetic",
        calibration_trusted: bool = True,
        road_plane_polygon_world: list[tuple[float, float]] | None = None,
        validation_max_error_px: float | None = None,
    ) -> HomographyGrid:
        if frame_width <= 0 or frame_height <= 0:
            raise ValueError("frame dimensions must be positive")
        if world_width_m <= 0 or world_length_m <= 0:
            raise ValueError("world dimensions must be positive")
        if spacing_m <= 0:
            raise ValueError("grid spacing must be positive")

        inverse_h = np.linalg.inv(homography.homography_matrix).astype(np.float64)
        clipping_polygon = road_plane_polygon_world or [
            (0.0, 0.0),
            (world_width_m, 0.0),
            (world_width_m, world_length_m),
            (0.0, world_length_m),
        ]
        vertical_xs = self._grid_values(world_width_m, spacing_m)
        horizontal_ys = self._grid_values(world_length_m, spacing_m)
        lines: list[HomographyGridLine] = []
        for x in vertical_xs:
            clipped = self._clip_segment_to_convex_polygon(
                (x, 0.0),
                (x, world_length_m),
                clipping_polygon,
            )
            if clipped is None:
                continue
            world_start, world_end = clipped
            lines.append(
                HomographyGridLine(
                    kind="longitudinal",
                    world_start=world_start,
                    world_end=world_end,
                    pixel_start=self._world_to_pixel(inverse_h, *world_start),
                    pixel_end=self._world_to_pixel(inverse_h, *world_end),
                ),
            )
        for y in horizontal_ys:
            clipped = self._clip_segment_to_convex_polygon(
                (0.0, y),
                (world_width_m, y),
                clipping_polygon,
            )
            if clipped is None:
                continue
            world_start, world_end = clipped
            lines.append(
                HomographyGridLine(
                    kind="lateral",
                    world_start=world_start,
                    world_end=world_end,
                    pixel_start=self._world_to_pixel(inverse_h, *world_start),
                    pixel_end=self._world_to_pixel(inverse_h, *world_end),
                ),
            )
        return HomographyGrid(
            frame_width=frame_width,
            frame_height=frame_height,
            spacing_m=spacing_m,
            world_width_m=world_width_m,
            world_length_m=world_length_m,
            generated_from="inverse_homography_projection",
            calibration_source=calibration_source,
            calibration_trusted=calibration_trusted,
            pixel_rmse_px=homography.world_to_pixel_rmse_px,
            world_rmse_m=homography.pixel_to_world_rmse_m,
            validation_max_error_px=validation_max_error_px,
            road_plane_polygon_world=clipping_polygon,
            lines=lines,
        )

    @staticmethod
    def _clip_segment_to_convex_polygon(
        start: tuple[float, float],
        end: tuple[float, float],
        polygon: list[tuple[float, float]],
    ) -> tuple[tuple[float, float], tuple[float, float]] | None:
        if len(polygon) < 3:
            return (start, end)
        area = 0.0
        for index, point in enumerate(polygon):
            next_point = polygon[(index + 1) % len(polygon)]
            area += point[0] * next_point[1] - next_point[0] * point[1]
        orientation = 1.0 if area >= 0 else -1.0
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        enter = 0.0
        leave = 1.0
        eps = 1e-9

        for index, edge_start in enumerate(polygon):
            edge_end = polygon[(index + 1) % len(polygon)]
            edge_x = edge_end[0] - edge_start[0]
            edge_y = edge_end[1] - edge_start[1]
            start_x = start[0] - edge_start[0]
            start_y = start[1] - edge_start[1]
            numerator = orientation * (edge_x * start_y - edge_y * start_x)
            denominator = orientation * (edge_x * dy - edge_y * dx)
            if abs(denominator) < eps:
                if numerator < -eps:
                    return None
                continue
            crossing = -numerator / denominator
            if denominator > 0:
                enter = max(enter, crossing)
            else:
                leave = min(leave, crossing)
            if enter - leave > eps:
                return None

        clipped_start = (start[0] + dx * enter, start[1] + dy * enter)
        clipped_end = (start[0] + dx * leave, start[1] + dy * leave)
        return (clipped_start, clipped_end)

    @staticmethod
    def _is_collinear(points: NDArray[np.float64]) -> bool:
        centered = points - np.mean(points, axis=0)
        return bool(np.linalg.matrix_rank(centered, tol=1e-9) < 2)

    @staticmethod
    def _grid_values(max_value: float, spacing: float) -> list[float]:
        values = [0.0]
        current = spacing
        while current < max_value:
            values.append(float(current))
            current += spacing
        if not math.isclose(values[-1], max_value):
            values.append(float(max_value))
        return values

    @staticmethod
    def _world_to_pixel(
        inverse_homography_matrix: NDArray[np.float64],
        world_x: float,
        world_y: float,
    ) -> tuple[float, float]:
        point = np.array([world_x, world_y, 1.0], dtype=float)
        projected = inverse_homography_matrix @ point
        projected = projected / projected[2]
        return (float(projected[0]), float(projected[1]))

    @staticmethod
    def _solve_dlt(
        pixel_points: NDArray[np.float64],
        world_points: NDArray[np.float64],
    ) -> tuple[NDArray[np.float64], float]:
        pixel_normalized, pixel_transform = CalibrationService._normalize_points(pixel_points)
        world_normalized, world_transform = CalibrationService._normalize_points(world_points)
        rows: list[list[float]] = []
        for (u, v), (x, y) in zip(pixel_normalized, world_normalized, strict=True):
            rows.append([u, v, 1.0, 0.0, 0.0, 0.0, -u * x, -v * x, -x])
            rows.append([0.0, 0.0, 0.0, u, v, 1.0, -u * y, -v * y, -y])
        a = np.array(rows, dtype=float)
        _, singular_values, vh = np.linalg.svd(a)
        h = vh[-1].reshape(3, 3)
        h = np.linalg.inv(world_transform) @ h @ pixel_transform
        if abs(h[2, 2]) > 1e-12:
            h = h / h[2, 2]
        condition_number = float(singular_values[0] / singular_values[-1])
        return h.astype(np.float64), condition_number

    @staticmethod
    def _refine_homography(
        matrix: NDArray[np.float64],
        pixel_points: NDArray[np.float64],
        world_points: NDArray[np.float64],
        validation_pixels: NDArray[np.float64] | None = None,
        validation_world: NDArray[np.float64] | None = None,
    ) -> tuple[NDArray[np.float64], bool, float, float, int | None]:
        initial_rmse = CalibrationService.compute_reprojection_error(
            CalibrationService(),
            matrix,
            pixel_points,
            world_points,
        )
        try:
            from scipy.optimize import least_squares
        except ImportError:
            return matrix, False, initial_rmse, initial_rmse, None

        def pack(homography: NDArray[np.float64]) -> NDArray[np.float64]:
            normalized = homography / homography[2, 2]
            return normalized.reshape(-1)[:8]

        def unpack(values: NDArray[np.float64]) -> NDArray[np.float64]:
            return np.array(
                [
                    [values[0], values[1], values[2]],
                    [values[3], values[4], values[5]],
                    [values[6], values[7], 1.0],
                ],
                dtype=np.float64,
            )

        def residuals(values: NDArray[np.float64]) -> NDArray[np.float64]:
            projected = CalibrationService._project_points(unpack(values), pixel_points)
            control_residuals = (projected - world_points).reshape(-1)
            if (
                validation_pixels is None
                or validation_world is None
                or len(validation_pixels) == 0
            ):
                return control_residuals
            validation_projected = CalibrationService._project_points(
                unpack(values),
                validation_pixels,
            )
            validation_residuals = (validation_projected - validation_world).reshape(-1)
            return np.concatenate([control_residuals, validation_residuals * 0.7])

        result = least_squares(
            residuals,
            pack(matrix),
            loss="huber",
            f_scale=0.5,
            max_nfev=80,
        )
        refined = unpack(result.x)
        final_rmse = CalibrationService.compute_reprojection_error(
            CalibrationService(),
            refined,
            pixel_points,
            world_points,
        )
        if not result.success or final_rmse > initial_rmse:
            return matrix, True, initial_rmse, initial_rmse, int(result.nfev)
        return refined.astype(np.float64), True, initial_rmse, final_rmse, int(result.nfev)

    @staticmethod
    def _validation_segment_points(
        validation_segments: list[dict[str, object]],
    ) -> tuple[NDArray[np.float64] | None, NDArray[np.float64] | None]:
        pixel_points: list[tuple[float, float]] = []
        world_points: list[tuple[float, float]] = []
        for segment in validation_segments:
            pixel_start = segment.get("pixel_start")
            pixel_end = segment.get("pixel_end")
            world_start = segment.get("world_start")
            world_end = segment.get("world_end")
            if not (
                isinstance(pixel_start, (list, tuple))
                and isinstance(pixel_end, (list, tuple))
                and isinstance(world_start, (list, tuple))
                and isinstance(world_end, (list, tuple))
                and len(pixel_start) == 2
                and len(pixel_end) == 2
                and len(world_start) == 2
                and len(world_end) == 2
            ):
                continue
            try:
                pixel_points.extend(
                    [
                        (float(pixel_start[0]), float(pixel_start[1])),
                        (float(pixel_end[0]), float(pixel_end[1])),
                    ]
                )
                world_points.extend(
                    [
                        (float(world_start[0]), float(world_start[1])),
                        (float(world_end[0]), float(world_end[1])),
                    ]
                )
            except (TypeError, ValueError):
                continue
        if not pixel_points:
            return None, None
        return (
            np.array(pixel_points, dtype=np.float64),
            np.array(world_points, dtype=np.float64),
        )

    @staticmethod
    def _normalize_points(
        points: NDArray[np.float64],
    ) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
        centroid = np.mean(points, axis=0)
        distances = np.linalg.norm(points - centroid, axis=1)
        mean_distance = float(np.mean(distances))
        scale = math.sqrt(2.0) / mean_distance if mean_distance > 1e-12 else 1.0
        transform = np.array(
            [
                [scale, 0.0, -scale * centroid[0]],
                [0.0, scale, -scale * centroid[1]],
                [0.0, 0.0, 1.0],
            ],
            dtype=float,
        )
        ones = np.ones((points.shape[0], 1), dtype=float)
        homogeneous = np.hstack([points, ones])
        normalized = homogeneous @ transform.T
        normalized = normalized / normalized[:, 2:3]
        return normalized[:, :2], transform

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
