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
            "foot_pixel",
            "contact_source",
            "contact_state",
            "measurement_policy",
            "contact_state_probabilities",
            "contact_phase_probabilities",
            "contact_covariance_px",
            "body_ground_projection",
            "support_contact_anchor",
            "foot_skate_risk",
            "pedestrian_periodic_calibration_consistency",
            "contact_episodes",
            "current_contact_episode_id",
            "current_contact_episode_phase",
            "support_velocity_mps",
            "support_zero_velocity_residual_mps",
            "speed_periodic_kmh",
            "body_periodic_speed_gap_kmh",
            "near_far_speed_drift_score",
            "geometry_status",
            "homography_sample_std_m",
            "scale_anchor_uncertainty_m",
            "jacobian_amplification",
            "point_homography_std_m",
            "point_jacobian_amplification",
            "point_extrapolation_risk",
            "point_metric_gate_reason",
            "real_speed_acceptance_status",
            "identity_switch_probability",
            "episode_stride_length_m",
            "episode_stride_time_sec",
            "golden_acceptance_verdict",
            "local_jacobian_speed_amplification_p95",
            "plane_id",
            "plane_kind",
            "plane_status",
            "explicit_metric_plane",
            "pedestrian_metric_admitted",
            "pedestrian_metric_rejection_reason",
            "bbox_contact_contaminated",
            "world_x",
            "world_y",
            "world_xy",
            "local_scale_factor",
            "local_scale_percentile",
            "position_covariance",
            "Sigma_world",
            "instantaneous_speed_kmh",
            "filtered_speed_kmh",
            "posterior_speed_p05_p50_p95_kmh",
            "dominant_uncertainty_source",
            "near_far_speed_drift_metrics",
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
                    "class_id": track.get("class_id"),
                    "class_name": track.get("class_name"),
                    "bbox_xyxy": track.get("xyxy"),
                    "bbox_height_px": diagnostics.get("bbox_height_px"),
                    "raw_bbox_foot": diagnostics.get("raw_bbox_foot"),
                    "fused_foot": diagnostics.get("fused_foot"),
                    "foot_pixel": diagnostics.get("fused_foot"),
                    "contact_source": track.get("contact_source")
                    or diagnostics.get("contact_source")
                    or track.get("measurement_source"),
                    "contact_state": track.get("contact_state")
                    or diagnostics.get("contact_state"),
                    "measurement_policy": track.get("measurement_policy")
                    or diagnostics.get("measurement_policy"),
                    "contact_state_probabilities": track.get(
                        "contact_state_probabilities",
                    )
                    or diagnostics.get("contact_state_probabilities"),
                    "contact_phase_probabilities": track.get(
                        "contact_phase_probabilities",
                    )
                    or diagnostics.get("contact_phase_probabilities"),
                    "contact_covariance_px": track.get("contact_pixel_covariance")
                    or diagnostics.get("contact_covariance_px"),
                    "body_ground_projection": track.get("body_ground_projection")
                    or diagnostics.get("body_ground_projection"),
                    "support_contact_anchor": track.get("support_contact_anchor")
                    or diagnostics.get("support_contact_anchor"),
                    "foot_skate_risk": track.get("foot_skate_risk")
                    or diagnostics.get("foot_skate_risk"),
                    "pedestrian_periodic_calibration_consistency": track.get(
                        "pedestrian_periodic_calibration_consistency",
                    )
                    or diagnostics.get("pedestrian_periodic_calibration_consistency"),
                    "contact_episodes": track.get("contact_episodes")
                    or diagnostics.get("contact_episodes"),
                    "current_contact_episode_id": diagnostics.get(
                        "current_contact_episode_id",
                    ),
                    "current_contact_episode_phase": diagnostics.get(
                        "current_contact_episode_phase",
                    ),
                    "support_velocity_mps": diagnostics.get("support_velocity_mps"),
                    "support_zero_velocity_residual_mps": track.get(
                        "support_zero_velocity_residual_mps",
                    )
                    or diagnostics.get("support_zero_velocity_residual_mps"),
                    "speed_periodic_kmh": track.get("speed_periodic_kmh")
                    or diagnostics.get("speed_periodic_kmh"),
                    "body_periodic_speed_gap_kmh": track.get(
                        "body_periodic_speed_gap_kmh",
                    )
                    or diagnostics.get("body_periodic_speed_gap_kmh"),
                    "near_far_speed_drift_score": track.get(
                        "near_far_speed_drift_score",
                    )
                    or diagnostics.get("near_far_speed_drift_score"),
                    "geometry_status": track.get("geometry_status")
                    or diagnostics.get("geometry_status"),
                    "homography_sample_std_m": diagnostics.get("homography_sample_std_m"),
                    "scale_anchor_uncertainty_m": diagnostics.get(
                        "scale_anchor_uncertainty_m",
                    ),
                    "jacobian_amplification": diagnostics.get("jacobian_amplification"),
                    "point_homography_std_m": track.get("point_homography_std_m")
                    or diagnostics.get("point_homography_std_m"),
                    "point_jacobian_amplification": track.get(
                        "point_jacobian_amplification",
                    )
                    or diagnostics.get("point_jacobian_amplification"),
                    "point_extrapolation_risk": track.get("point_extrapolation_risk")
                    or diagnostics.get("point_extrapolation_risk"),
                    "point_metric_gate_reason": track.get("point_metric_gate_reason")
                    or diagnostics.get("point_metric_gate_reason"),
                    "real_speed_acceptance_status": track.get(
                        "real_speed_acceptance_status",
                    )
                    or diagnostics.get("real_speed_acceptance_status"),
                    "identity_switch_probability": (
                        (track.get("identity_posterior") or {}).get(
                            "id_switch_probability",
                        )
                        if isinstance(track.get("identity_posterior"), dict)
                        else None
                    ),
                    "episode_stride_length_m": diagnostics.get("episode_stride_length_m"),
                    "episode_stride_time_sec": diagnostics.get("episode_stride_time_sec"),
                    "local_jacobian_speed_amplification_p95": diagnostics.get(
                        "local_jacobian_speed_amplification_p95",
                    ),
                    "plane_id": track.get("plane_id") or diagnostics.get("plane_id"),
                    "plane_kind": diagnostics.get("plane_kind"),
                    "plane_status": diagnostics.get("plane_status"),
                    "explicit_metric_plane": diagnostics.get("explicit_metric_plane"),
                    "pedestrian_metric_admitted": diagnostics.get(
                        "pedestrian_metric_admitted",
                    ),
                    "pedestrian_metric_rejection_reason": diagnostics.get(
                        "pedestrian_metric_rejection_reason",
                    ),
                    "bbox_contact_contaminated": diagnostics.get(
                        "bbox_contact_contaminated",
                    ),
                    "world_x": world[0] if world is not None else None,
                    "world_y": world[1] if world is not None else None,
                    "world_xy": list(world) if world is not None else None,
                    "local_scale_factor": track.get("local_scale_factor"),
                    "local_scale_percentile": track.get("local_scale_percentile"),
                    "position_covariance": track.get("world_position_covariance")
                    or track.get("position_covariance"),
                    "Sigma_world": track.get("world_position_covariance")
                    or track.get("position_covariance"),
                    "instantaneous_speed_kmh": instantaneous_speed,
                    "filtered_speed_kmh": track.get("speed_kmh"),
                    "posterior_speed_p05_p50_p95_kmh": (
                        (
                            track.get("joint_physics_posterior_v5")
                            or track.get("joint_physics_posterior")
                            or {}
                        ).get(
                            "speed_p05_p50_p95_kmh",
                        )
                        if isinstance(
                            track.get("joint_physics_posterior_v5")
                            or track.get("joint_physics_posterior"),
                            dict,
                        )
                        else None
                    ),
                    "dominant_uncertainty_source": track.get(
                        "dominant_uncertainty_source",
                    )
                    or (
                        (
                            track.get("joint_physics_posterior_v5")
                            or track.get("joint_physics_posterior")
                            or {}
                        ).get(
                            "dominant_uncertainty_source",
                        )
                        if isinstance(
                            track.get("joint_physics_posterior_v5")
                            or track.get("joint_physics_posterior"),
                            dict,
                        )
                        else None
                    ),
                    "near_far_speed_drift_metrics": track.get(
                        "near_far_speed_drift_metrics",
                    )
                    or (
                        (
                            track.get("joint_physics_posterior_v5")
                            or track.get("joint_physics_posterior")
                            or {}
                        ).get(
                            "near_far_speed_drift_metrics",
                        )
                        if isinstance(
                            track.get("joint_physics_posterior_v5")
                            or track.get("joint_physics_posterior"),
                            dict,
                        )
                        else None
                    ),
                    "physics_valid": track.get("physics_valid"),
                    "rejection_reason": track.get("rejection_reason"),
                }
            )
        metrics = self._metrics(rows)
        golden = metrics.get("golden_acceptance")
        if isinstance(golden, dict):
            for row in rows:
                row["golden_acceptance_verdict"] = golden.get("passed")
        return TrackGeometryDiagnostic(
            tracker_id=tracker_id,
            rows=rows,
            metrics=metrics,
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
            "foot_skate_risk_p95": _percentile(
                _numbers(row.get("foot_skate_risk") for row in rows),
                95.0,
            ),
            "pedestrian_periodic_calibration_consistency_mean": _mean_or_none(
                _numbers(
                    row.get("pedestrian_periodic_calibration_consistency")
                    for row in rows
                ),
            ),
            "support_zero_velocity_residual_p95_mps": _percentile(
                _numbers(row.get("support_zero_velocity_residual_mps") for row in rows),
                95.0,
            ),
            "periodic_body_speed_gap_mean_kmh": _mean_or_none(
                _numbers(row.get("body_periodic_speed_gap_kmh") for row in rows),
            ),
            "near_far_speed_drift_score_p95": _percentile(
                _numbers(row.get("near_far_speed_drift_score") for row in rows),
                95.0,
            ),
            "golden_acceptance": _golden_acceptance(rows, speeds, scales, inverse_heights),
            "perspective_coupled_speed_drift": _perspective_coupled(
                speeds,
                scales,
                inverse_heights,
            ),
            "root_cause_verdicts": _root_cause_verdicts(rows, speeds, scales, inverse_heights),
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


def _mean_or_none(values: list[float]) -> float | None:
    return float(mean(values)) if values else None


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    if len(values) == 1:
        return float(values[0])
    ordered = sorted(values)
    index = (len(ordered) - 1) * max(0.0, min(100.0, percentile)) / 100.0
    lower = int(math.floor(index))
    upper = int(math.ceil(index))
    if lower == upper:
        return float(ordered[lower])
    fraction = index - lower
    return float(ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction)


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


def _root_cause_verdicts(
    rows: list[dict[str, object]],
    speeds: list[float],
    scales: list[float],
    inverse_heights: list[float],
) -> list[str]:
    verdicts: list[str] = []
    if any(_is_pedestrian(row) and not _truthy(row.get("explicit_metric_plane")) for row in rows):
        verdicts.append("missing_pedestrian_metric_plane")
    if any(
        _is_pedestrian(row)
        and (
            str(row.get("plane_kind") or "").lower() == "road"
            or str(row.get("plane_status") or "").lower() == "default"
        )
        for row in rows
    ):
        verdicts.append("wrong_plane_likely")
    if any(_truthy(row.get("bbox_contact_contaminated")) for row in rows):
        verdicts.append("bbox_contact_contaminated")
    if any(
        (risk is not None and risk >= 0.6)
        for risk in (_optional_float(row.get("foot_skate_risk")) for row in rows)
    ):
        verdicts.append("foot_skate_or_geometry_risk")
    if any(
        str(row.get("measurement_policy") or "") in {"reject", "predict_only"}
        for row in rows
    ):
        verdicts.append("contact_state_unstable")
    if any(str(row.get("dominant_uncertainty_source") or "") == "Sigma_H" for row in rows):
        verdicts.append("Sigma_H_dominant")
    if any("tracking" in str(row.get("dominant_uncertainty_source") or "") for row in rows):
        verdicts.append("tracking_identity_risk")
    if any("coordinate_space" in str(row.get("contact_source") or "") for row in rows):
        verdicts.append("coordinate_space_mismatch")
    if _perspective_coupled(speeds, scales, inverse_heights):
        verdicts.append("perspective_coupled_speed_drift")
    if any(
        str(row.get("geometry_status") or "")
        in {"periodic_inconsistent", "body_periodic_inconsistent"}
        for row in rows
    ):
        verdicts.append("body_periodic_inconsistent")
    if any(str(row.get("geometry_status") or "") == "weak_scale" for row in rows):
        verdicts.append("near_far_scale_drift")
    if any(
        str(row.get("geometry_status") or "")
        in {"foot_skate_invalid", "foot_skate_or_wrong_geometry"}
        for row in rows
    ):
        verdicts.append("foot_skate_or_wrong_geometry")
    if any(
        _optional_float(row.get("identity_switch_probability")) is not None
        and _optional_float(row.get("identity_switch_probability")) >= 0.5
        for row in rows
    ):
        verdicts.append("identity_switch_risk")
    if any(
        str(row.get("pedestrian_metric_rejection_reason") or "")
        == "homography_posterior_too_wide"
        for row in rows
    ):
        verdicts.append("homography_posterior_too_wide")
    if any(
        str(row.get("pedestrian_metric_rejection_reason") or "")
        == "jacobian_amplification_high"
        for row in rows
    ):
        verdicts.append("jacobian_amplification_high")
    if any(
        str(row.get("point_metric_gate_reason") or "") == "outside_metric_plane_support"
        for row in rows
    ):
        verdicts.append("outside_metric_plane_support")
    if any(
        str(row.get("point_metric_gate_reason") or "")
        == "jacobian_amplification_high"
        for row in rows
    ):
        verdicts.append("jacobian_amplification_high")
    if any(
        str(row.get("pedestrian_metric_rejection_reason") or "") == "intrinsics_unverified"
        for row in rows
    ):
        verdicts.append("intrinsics_or_distortion_likely")
    return verdicts


def _golden_acceptance(
    rows: list[dict[str, object]],
    speeds: list[float],
    scales: list[float],
    inverse_heights: list[float],
) -> dict[str, object]:
    speed_cv = _coefficient_of_variation(speeds)
    scale_corr = _correlation(speeds, scales)
    height_corr = _correlation(speeds[: len(inverse_heights)], inverse_heights)
    foot_skate_p95 = _percentile(_numbers(row.get("foot_skate_risk") for row in rows), 95.0)
    periodic_mean = _mean_or_none(
        _numbers(row.get("pedestrian_periodic_calibration_consistency") for row in rows),
    )
    drift_p95 = _percentile(
        _numbers(row.get("near_far_speed_drift_score") for row in rows),
        95.0,
    )
    checks = {
        "speed_cv_lt_0_25": speed_cv is not None and speed_cv < 0.25,
        "speed_local_scale_corr_lt_0_35": (
            scale_corr is not None and abs(scale_corr) < 0.35
        ),
        "speed_inverse_height_corr_lt_0_35": (
            height_corr is not None and abs(height_corr) < 0.35
        ),
        "foot_skate_p95_lt_0_35": foot_skate_p95 is not None and foot_skate_p95 < 0.35,
        "periodic_consistency_mean_gt_0_6": (
            periodic_mean is not None and periodic_mean > 0.6
        ),
        "near_far_drift_score_lt_0_35": drift_p95 is not None and drift_p95 < 0.35,
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "speed_cv": speed_cv,
        "speed_local_scale_correlation": scale_corr,
        "speed_inverse_height_correlation": height_corr,
        "foot_skate_risk_p95": foot_skate_p95,
        "pedestrian_periodic_calibration_consistency_mean": periodic_mean,
        "near_far_speed_drift_score_p95": drift_p95,
        "model_reference": "pedestrian_golden_acceptance_v6",
    }


def _is_pedestrian(row: dict[str, object]) -> bool:
    class_id = row.get("class_id")
    class_name = str(row.get("class_name") or "").lower()
    return class_id == 0 or class_name == "person"


def _truthy(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in {"1", "true", "yes"}
    return bool(value)


def _csv_value(value: object) -> object:
    if isinstance(value, list | dict):
        return json.dumps(value, ensure_ascii=False)
    return value
