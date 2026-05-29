from __future__ import annotations

import math

import numpy as np

from domain.crowd_density.models import CrowdDensityInput, CrowdDensityResult


class CrowdDensityService:
    def analyze(self, request: CrowdDensityInput) -> CrowdDensityResult:
        area_sqm = max(request.region_width_m * request.region_length_m, 1e-6)
        if request.direct_detection_count < request.trigger_threshold:
            density = request.direct_detection_count / area_sqm
            return CrowdDensityResult(
                region_name=request.region_name,
                people_count=request.direct_detection_count,
                direct_detection_count=request.direct_detection_count,
                integrated_people_count=float(request.direct_detection_count),
                density_people_per_sqm=float(density),
                peak_density_people_per_sqm=float(density),
                estimation_method="direct_detection_count",
                density_integral_triggered=False,
                crowding_level=self._crowding_level(density),
                density_field={
                    "cell_size_m": request.cell_size_m,
                    "kernel_bandwidth_m": request.kernel_bandwidth_m,
                    "cells_x": 0,
                    "cells_y": 0,
                    "visible_area_sqm": area_sqm,
                },
            )

        density_grid = self._estimate_density_grid(request)
        cell_area = request.cell_size_m * request.cell_size_m
        raw_integral = float(density_grid.sum() * cell_area)
        peak_density = float(density_grid.max()) if density_grid.size else 0.0
        correction = self._occlusion_correction(
            request.direct_detection_count,
            request.trigger_threshold,
            peak_density,
        )
        integrated_count = max(
            float(request.direct_detection_count),
            raw_integral * correction,
        )
        density = integrated_count / area_sqm
        return CrowdDensityResult(
            region_name=request.region_name,
            people_count=int(math.ceil(integrated_count)),
            direct_detection_count=request.direct_detection_count,
            integrated_people_count=float(integrated_count),
            density_people_per_sqm=float(density),
            peak_density_people_per_sqm=peak_density,
            estimation_method="density_field_integral",
            density_integral_triggered=True,
            crowding_level=self._crowding_level(density),
            density_field={
                "cell_size_m": request.cell_size_m,
                "kernel_bandwidth_m": request.kernel_bandwidth_m,
                "cells_x": int(density_grid.shape[1]) if density_grid.ndim == 2 else 0,
                "cells_y": int(density_grid.shape[0]) if density_grid.ndim == 2 else 0,
                "visible_area_sqm": area_sqm,
                "raw_integral_people": raw_integral,
                "occlusion_correction_factor": correction,
            },
        )

    @staticmethod
    def _estimate_density_grid(request: CrowdDensityInput) -> np.ndarray:
        cell = max(request.cell_size_m, 0.25)
        bandwidth = max(request.kernel_bandwidth_m, cell)
        xs = np.arange(cell / 2.0, request.region_width_m, cell, dtype=float)
        ys = np.arange(cell / 2.0, request.region_length_m, cell, dtype=float)
        if len(xs) == 0 or len(ys) == 0:
            return np.zeros((0, 0), dtype=float)
        grid_x, grid_y = np.meshgrid(xs, ys)
        density = np.zeros_like(grid_x, dtype=float)
        cell_area = cell * cell
        for raw_x, raw_y in request.points_m:
            if not math.isfinite(raw_x) or not math.isfinite(raw_y):
                continue
            x = min(max(raw_x, 0.0), request.region_width_m)
            y = min(max(raw_y, 0.0), request.region_length_m)
            squared_distance = (grid_x - x) ** 2 + (grid_y - y) ** 2
            kernel = np.exp(-squared_distance / (2.0 * bandwidth * bandwidth))
            visible_mass = float(kernel.sum() * cell_area)
            if visible_mass > 1e-9:
                density += kernel / visible_mass
        return density

    @staticmethod
    def _occlusion_correction(
        direct_detection_count: int,
        trigger_threshold: int,
        peak_density: float,
    ) -> float:
        count_pressure = max(0.0, (direct_detection_count - trigger_threshold) / trigger_threshold)
        density_pressure = min(1.0, peak_density / 0.8)
        return min(1.8, 1.0 + 0.35 * count_pressure + 0.15 * density_pressure)

    @staticmethod
    def _crowding_level(density_people_per_sqm: float) -> str:
        if density_people_per_sqm >= 2.5:
            return "critical"
        if density_people_per_sqm >= 1.2:
            return "crowded"
        if density_people_per_sqm >= 0.35:
            return "busy"
        return "normal"
