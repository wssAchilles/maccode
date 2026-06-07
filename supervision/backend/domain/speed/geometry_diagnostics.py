from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, pstdev
from typing import Any


@dataclass(frozen=True)
class TrackGeometryDiagnostic:
    tracker_id: int
    rows: list[dict[str, object]]
    metrics: dict[str, object]

    def write_csv(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = [
            "frame_index",
            "timestamp_sec",
            "tracker_id",
            "class_name",
            "bbox_xyxy",
            "bbox_height_px",
            "raw_bbox_foot",
            "fused_foot",
            "contact_source",
            "contact_covariance_px",
            "plane_id",
            "plane_status",
            "world_x",
            "world_y",
            "local_scale_factor",
            "local_scale_percentile",
            "position_covariance",
            "instantaneous_speed_kmh",
            "filtered_speed_kmh",
            "physics_valid",
            "rejection_reason",
        ]
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for row in self.rows:
                writer.writerow({key: _csv_value(row.get(key)) for key in fieldnames})

    def write_json(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "tracker_id": self.tracker_id,
                    "metrics": self.metrics,
                    "rows": self.rows,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )


class TrackGeometryDiagnosticBuilder:
    def build(
        self,
        reports: list[dict[str, Any]],
        *,
        tracker_id: int,
    ) -> TrackGeometryDiagnostic:
        rows: list[dict[str, object]] = []
        previous_world: tuple[float, float] | None = None
        previous_timestamp: float | None = None
        for report in sorted(reports, key=lambda item: float(item.get("timestamp_sec", 0.0))):
            track = self._track(report, tracker_id)
            if track is None:
                continue
            diagnostics = track.get("speed_geometry_diagnostics")
            diagnostics = diagnostics if isinstance(diagnostics, dict) else {}
            world = self._world(track)
            timestamp = _optional_float(report.get("timestamp_sec"))
            instantaneous_speed = None
            if (
                world is not None
                and previous_world is not None
                and timestamp is not None
                and previous_timestamp is not None
                and timestamp > previous_timestamp
            ):
                instantaneous_speed = math.dist(previous_world, world) / (
                    timestamp - previous_timestamp
                ) * 3.6
            if world is not None and timestamp is not None:
                previous_world = world
                previous_timestamp = timestamp
            rows.append(
                {
                    "frame_index": report.get("frame_index"),
                    "timestamp_sec": timestamp,
                    "tracker_id": tracker_id,
                    "class_name": track.get("class_name"),
                    "bbox_xyxy": track.get("xyxy"),
                    "bbox_height_px": diagnostics.get("bbox_height_px"),
                    "raw_bbox_foot": diagnostics.get("raw_bbox_foot"),
                    "fused_foot": diagnostics.get("fused_foot"),
                    "contact_source": track.get("contact_source")
                    or diagnostics.get("contact_source")
                    or track.get("measurement_source"),
                    "contact_covariance_px": track.get("contact_pixel_covariance")
                    or diagnostics.get("contact_covariance_px"),
                    "plane_id": track.get("plane_id") or diagnostics.get("plane_id"),
                    "plane_status": diagnostics.get("plane_status"),
                    "world_x": world[0] if world is not None else None,
                    "world_y": world[1] if world is not None else None,
                    "local_scale_factor": track.get("local_scale_factor"),
                    "local_scale_percentile": track.get("local_scale_percentile"),
                    "position_covariance": track.get("world_position_covariance")
                    or track.get("position_covariance"),
                    "instantaneous_speed_kmh": instantaneous_speed,
                    "filtered_speed_kmh": track.get("speed_kmh"),
                    "physics_valid": track.get("physics_valid"),
                    "rejection_reason": track.get("rejection_reason"),
                }
            )
        return TrackGeometryDiagnostic(
            tracker_id=tracker_id,
            rows=rows,
            metrics=self._metrics(rows),
        )

    @staticmethod
    def _track(report: dict[str, Any], tracker_id: int) -> dict[str, Any] | None:
        tracks = report.get("active_tracks")
        if not isinstance(tracks, list):
            return None
        for track in tracks:
            if isinstance(track, dict) and int(track.get("tracker_id", -1)) == tracker_id:
                return track
        return None

    @staticmethod
    def _world(track: dict[str, Any]) -> tuple[float, float] | None:
        x = _optional_float(track.get("ground_x_m"))
        y = _optional_float(track.get("ground_y_m"))
        if x is None or y is None:
            return None
        return (x, y)

    @staticmethod
    def _metrics(rows: list[dict[str, object]]) -> dict[str, object]:
        speeds = _numbers(row.get("filtered_speed_kmh") for row in rows)
        scales = _numbers(row.get("local_scale_factor") for row in rows)
        heights = _numbers(row.get("bbox_height_px") for row in rows)
        inverse_heights = [1.0 / value for value in heights if value > 0]
        fused_points = [
            value
            for value in (row.get("fused_foot") for row in rows)
            if isinstance(value, list) and len(value) == 2
        ]
        return {
            "sample_count": len(rows),
            "speed_cv": _coefficient_of_variation(speeds),
            "speed_local_scale_correlation": _correlation(speeds, scales),
            "speed_inverse_bbox_height_correlation": _correlation(
                speeds[: len(inverse_heights)],
                inverse_heights,
            ),
            "world_path_residual_m": _world_path_residual(rows),
            "footpoint_jitter_px": _point_jitter(fused_points),
            "perspective_coupled_speed_drift": _perspective_coupled(
                speeds,
                scales,
                inverse_heights,
            ),
        }


def reports_from_analysis_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    frame_reports = payload.get("frame_reports")
    if isinstance(frame_reports, list):
        return [item for item in frame_reports if isinstance(item, dict)]
    reports = payload.get("reports")
    if isinstance(reports, list):
        return [item for item in reports if isinstance(item, dict)]
    final_report = payload.get("final_report")
    if isinstance(final_report, dict):
        return [final_report]
    return [payload]


def _numbers(values: Any) -> list[float]:
    numbers: list[float] = []
    for value in values:
        parsed = _optional_float(value)
        if parsed is not None and math.isfinite(parsed):
            numbers.append(parsed)
    return numbers


def _optional_float(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if not isinstance(value, (int, float, str)):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _correlation(left: list[float], right: list[float]) -> float | None:
    count = min(len(left), len(right))
    if count < 3:
        return None
    left_values = left[:count]
    right_values = right[:count]
    left_mean = mean(left_values)
    right_mean = mean(right_values)
    left_std = pstdev(left_values)
    right_std = pstdev(right_values)
    if left_std <= 1e-9 or right_std <= 1e-9:
        return None
    covariance = mean(
        (left_value - left_mean) * (right_value - right_mean)
        for left_value, right_value in zip(left_values, right_values, strict=True)
    )
    return float(covariance / (left_std * right_std))


def _coefficient_of_variation(values: list[float]) -> float | None:
    if len(values) < 2:
        return None
    value_mean = mean(values)
    if abs(value_mean) <= 1e-9:
        return None
    return float(pstdev(values) / abs(value_mean))


def _world_path_residual(rows: list[dict[str, object]]) -> float | None:
    points = [
        (float(row["world_x"]), float(row["world_y"]))
        for row in rows
        if row.get("world_x") is not None and row.get("world_y") is not None
    ]
    if len(points) < 3:
        return None
    start = points[0]
    end = points[-1]
    line_dx = end[0] - start[0]
    line_dy = end[1] - start[1]
    norm = math.hypot(line_dx, line_dy)
    if norm <= 1e-9:
        return None
    residuals = [
        abs(line_dy * x - line_dx * y + end[0] * start[1] - end[1] * start[0]) / norm
        for x, y in points
    ]
    return float(mean(residuals))


def _point_jitter(points: list[object]) -> float | None:
    parsed = [
        (float(point[0]), float(point[1]))
        for point in points
        if isinstance(point, list) and len(point) == 2
    ]
    if len(parsed) < 3:
        return None
    deltas = [math.dist(left, right) for left, right in zip(parsed, parsed[1:], strict=False)]
    return float(pstdev(deltas)) if len(deltas) >= 2 else None


def _perspective_coupled(
    speeds: list[float],
    scales: list[float],
    inverse_heights: list[float],
) -> bool:
    scale_corr = _correlation(speeds, scales)
    height_corr = _correlation(speeds[: len(inverse_heights)], inverse_heights)
    return bool(
        (scale_corr is not None and abs(scale_corr) >= 0.6)
        or (height_corr is not None and abs(height_corr) >= 0.6)
    )


def _csv_value(value: object) -> object:
    if isinstance(value, list | dict):
        return json.dumps(value, ensure_ascii=False)
    return value
