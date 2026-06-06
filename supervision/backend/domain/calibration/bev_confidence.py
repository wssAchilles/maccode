from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np

from domain.speed.view_transformer import ViewTransformer

BEVRiskLevel = Literal["trusted", "caution", "rejected"]
RawBEVCell = tuple[
    tuple[float, float],
    tuple[float, float] | None,
    float,
    float,
    str | None,
]


@dataclass(frozen=True)
class BEVConfidenceCell:
    pixel: tuple[float, float]
    world: tuple[float, float] | None
    local_scale_factor: float
    position_sigma_m: float
    local_scale_percentile: float
    risk_level: BEVRiskLevel
    risk_reason: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "pixel": [self.pixel[0], self.pixel[1]],
            "world": [self.world[0], self.world[1]] if self.world is not None else None,
            "local_scale_factor": self.local_scale_factor,
            "position_sigma_m": self.position_sigma_m,
            "local_scale_percentile": self.local_scale_percentile,
            "risk_level": self.risk_level,
            "risk_reason": self.risk_reason,
        }


@dataclass(frozen=True)
class BEVRiskAssessment:
    risk_level: BEVRiskLevel
    risk_reason: str | None
    local_scale_factor: float
    position_sigma_m: float
    local_scale_percentile: float


@dataclass(frozen=True)
class BEVConfidenceMap:
    frame_width: int
    frame_height: int
    p75_local_scale: float
    p95_local_scale: float
    cells: list[BEVConfidenceCell]

    def assess(self, pixel: tuple[float, float]) -> BEVRiskAssessment:
        if not self.cells:
            return BEVRiskAssessment("caution", "empty_bev_confidence_map", 1.0, 0.0, 0.0)
        nearest = min(
            self.cells,
            key=lambda cell: (cell.pixel[0] - pixel[0]) ** 2 + (cell.pixel[1] - pixel[1]) ** 2,
        )
        return BEVRiskAssessment(
            risk_level=nearest.risk_level,
            risk_reason=nearest.risk_reason,
            local_scale_factor=nearest.local_scale_factor,
            position_sigma_m=nearest.position_sigma_m,
            local_scale_percentile=nearest.local_scale_percentile,
        )

    def to_dict(self) -> dict[str, object]:
        total = max(len(self.cells), 1)
        counts = {
            level: sum(1 for cell in self.cells if cell.risk_level == level)
            for level in ("trusted", "caution", "rejected")
        }
        return {
            "frame_width": self.frame_width,
            "frame_height": self.frame_height,
            "p75_local_scale": self.p75_local_scale,
            "p95_local_scale": self.p95_local_scale,
            "risk_counts": counts,
            "risk_ratios": {level: count / total for level, count in counts.items()},
            "cells": [cell.to_dict() for cell in self.cells],
        }


class BEVConfidenceMapBuilder:
    def __init__(
        self,
        view_transformer: ViewTransformer,
        *,
        frame_width: int,
        frame_height: int,
        road_plane_polygon_world: list[tuple[float, float]] | None = None,
        validation_max_error_px: float | None = None,
        grid_cols: int = 8,
        grid_rows: int = 6,
    ) -> None:
        self.view_transformer = view_transformer
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.road_plane_polygon_world = road_plane_polygon_world
        self.validation_max_error_px = validation_max_error_px
        self.grid_cols = max(2, grid_cols)
        self.grid_rows = max(2, grid_rows)

    def build(self) -> BEVConfidenceMap:
        raw_cells: list[RawBEVCell] = []
        scales: list[float] = []
        for row in range(self.grid_rows):
            y = self.frame_height * (row + 0.5) / self.grid_rows
            for col in range(self.grid_cols):
                x = self.frame_width * (col + 0.5) / self.grid_cols
                reason: str | None = None
                try:
                    uncertainty = self.view_transformer.local_position_uncertainty(x, y)
                    world = self.view_transformer.transform_point(x, y)
                    local_scale = float(uncertainty.local_scale_factor)
                    sigma = float(uncertainty.position_sigma_m)
                    if self.road_plane_polygon_world is not None and not self._point_in_polygon(
                        world,
                        self.road_plane_polygon_world,
                    ):
                        reason = "outside_calibrated_road_plane"
                except ValueError:
                    world = None
                    local_scale = 99.0
                    sigma = 99.0
                    reason = "homography_denominator_near_zero"
                raw_cells.append(((x, y), world, local_scale, sigma, reason))
                scales.append(local_scale)
        p75 = float(np.percentile(np.asarray(scales, dtype=np.float64), 75))
        p95 = float(np.percentile(np.asarray(scales, dtype=np.float64), 95))
        cells = [
            BEVConfidenceCell(
                pixel=pixel,
                world=world,
                local_scale_factor=local_scale,
                position_sigma_m=sigma,
                local_scale_percentile=self._percentile_rank(scales, local_scale),
                risk_level=self._risk_level(local_scale, p75, p95, reason),
                risk_reason=self._risk_reason(local_scale, p75, p95, reason),
            )
            for pixel, world, local_scale, sigma, reason in raw_cells
        ]
        return BEVConfidenceMap(
            frame_width=self.frame_width,
            frame_height=self.frame_height,
            p75_local_scale=p75,
            p95_local_scale=p95,
            cells=cells,
        )

    def _risk_level(
        self,
        local_scale: float,
        p75: float,
        p95: float,
        reason: str | None,
    ) -> BEVRiskLevel:
        if reason == "homography_denominator_near_zero":
            return "rejected"
        if self.validation_max_error_px is not None and self.validation_max_error_px > 25.0:
            return "rejected"
        if local_scale > max(p95, 1.0):
            return "rejected"
        if reason is not None or local_scale > max(p75, 1.0):
            return "caution"
        return "trusted"

    def _risk_reason(
        self,
        local_scale: float,
        p75: float,
        p95: float,
        reason: str | None,
    ) -> str | None:
        if reason is not None:
            return reason
        if self.validation_max_error_px is not None and self.validation_max_error_px > 25.0:
            return "validation_error_high"
        if local_scale > max(p95, 1.0):
            return "local_scale_above_p95"
        if local_scale > max(p75, 1.0):
            return "local_scale_above_p75"
        return None

    @staticmethod
    def _percentile_rank(values: list[float], value: float) -> float:
        if not values:
            return 0.0
        below = sum(1 for item in values if item <= value)
        return below / len(values)

    @staticmethod
    def _point_in_polygon(
        point: tuple[float, float],
        polygon: list[tuple[float, float]],
    ) -> bool:
        x, y = point
        inside = False
        j = len(polygon) - 1
        for i, (xi, yi) in enumerate(polygon):
            xj, yj = polygon[j]
            if ((yi > y) != (yj > y)) and (
                x < (xj - xi) * (y - yi) / max(yj - yi, 1e-12) + xi
            ):
                inside = not inside
            j = i
        return inside
