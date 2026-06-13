from __future__ import annotations

from collections import Counter, defaultdict
from statistics import median
from typing import Any

from domain.speed.pedestrian_quality import (
    PEDESTRIAN_ID_SWITCH_DISPLAY_THRESHOLD,
    PERSON_CLASS_ID,
)
from domain.speed.vehicle_diagnostics import build_vehicle_speed_aggregate

PEDESTRIAN_SPEED_REPORT_SCHEMA_VERSION = "pedestrian_speed_report_v1"
PEDESTRIAN_ACCEPTANCE_MIN_COVERAGE = 0.995
PEDESTRIAN_MAX_SPEED_KMH = 18.0
PEDESTRIAN_LOW_CONFIDENCE_THRESHOLD = 0.15
PEDESTRIAN_HIGH_UNCERTAINTY_BASE_KMH = 8.0
PEDESTRIAN_HIGH_UNCERTAINTY_SPEED_RATIO = 0.75
DISPLAYED_HIGH_UNCERTAINTY_MAX_RATIO = 0.02
DISPLAYED_LOW_CONFIDENCE_MAX_RATIO = 0.03
VEHICLE_SPEED_ROLE = "vehicle_speed"
PEDESTRIAN_SPEED_ROLE = "pedestrian_speed"


def build_pedestrian_speed_audit(
    frame_reports: list[dict[str, Any]],
    *,
    clip: str | None = None,
    clip_acceptance_min_coverage: float = PEDESTRIAN_ACCEPTANCE_MIN_COVERAGE,
    pedestrian_max_speed_kmh: float = PEDESTRIAN_MAX_SPEED_KMH,
) -> dict[str, Any]:
    counts: Counter[str] = Counter()
    na_by_reason: Counter[str] = Counter()
    display_state_counts: Counter[str] = Counter()
    source_counts: Counter[str] = Counter()
    contact_state_counts: Counter[str] = Counter()
    geometry_reason_counts: Counter[str] = Counter()
    speeds_by_track: defaultdict[int, list[tuple[int, float, float]]] = defaultdict(list)
    hidden_id_switch_risks: list[float] = []
    max_speed = 0.0

    for fallback_index, report in enumerate(frame_reports):
        frame_index = _frame_index(report, fallback_index)
        timestamp = _timestamp_sec(report, frame_index)
        for track in report.get("active_tracks", []):
            if not isinstance(track, dict) or not _is_pedestrian(track):
                continue
            counts["pedestrian_track_samples"] += 1
            source_counts[_speed_source(track)] += 1
            contact_state_counts[str(track.get("contact_state") or "unknown")] += 1
            geometry_reason = _geometry_reason(track)
            if geometry_reason:
                geometry_reason_counts[geometry_reason] += 1
            displayable = _is_displayable(track)
            display_state = _display_state(track, displayable)
            display_state_counts[display_state] += 1
            if displayable:
                counts["displayable_pedestrian_track_samples"] += 1
                speed = float(track["speed_kmh"])
                max_speed = max(max_speed, speed)
                tracker_id = int(track.get("tracker_id", -1))
                speeds_by_track[tracker_id].append((frame_index, timestamp, speed))
                if _is_low_confidence(track):
                    counts["displayed_low_confidence_count"] += 1
                if _is_high_uncertainty(track):
                    counts["displayed_high_uncertainty_count"] += 1
                if _id_switch_risk(track) >= PEDESTRIAN_ID_SWITCH_DISPLAY_THRESHOLD:
                    counts["displayed_id_switch_risk_count"] += 1
                if speed > pedestrian_max_speed_kmh:
                    counts["displayed_speed_limit_violation_count"] += 1
                if _has_residual_rejection_reason(track):
                    counts["displayed_residual_rejection_reason_count"] += 1
                if bool(track.get("fixed_lag_backfilled")) or bool(track.get("reconstructed")):
                    counts["fixed_lag_backfill_count"] += 1
                continue

            reason = _hidden_reason(track)
            na_by_reason[reason] += 1
            if _id_switch_risk(track) >= PEDESTRIAN_ID_SWITCH_DISPLAY_THRESHOLD:
                counts["hidden_id_switch_risk_count"] += 1
                hidden_id_switch_risks.append(_id_switch_risk(track))

    speed_jumps = _speed_jump_values(speeds_by_track)
    total = counts["pedestrian_track_samples"]
    displayable = counts["displayable_pedestrian_track_samples"]
    low_confidence = counts["displayed_low_confidence_count"]
    high_uncertainty = counts["displayed_high_uncertainty_count"]
    coverage = displayable / total if total else None
    low_ratio = low_confidence / displayable if displayable else 0.0
    high_ratio = high_uncertainty / displayable if displayable else 0.0
    return {
        "clip": clip,
        "report_schema_version": PEDESTRIAN_SPEED_REPORT_SCHEMA_VERSION,
        "pedestrian_track_samples": total,
        "displayable_pedestrian_track_samples": displayable,
        "pedestrian_display_coverage": coverage,
        "coverage_used_for_acceptance": coverage,
        "displayed_low_confidence_count": low_confidence,
        "displayed_low_confidence_ratio": low_ratio,
        "displayed_high_uncertainty_count": high_uncertainty,
        "displayed_high_uncertainty_ratio": high_ratio,
        "displayed_id_switch_risk_count": counts["displayed_id_switch_risk_count"],
        "displayed_speed_limit_violation_count": counts[
            "displayed_speed_limit_violation_count"
        ],
        "displayed_residual_rejection_reason_count": counts[
            "displayed_residual_rejection_reason_count"
        ],
        "hidden_id_switch_risk_count": counts["hidden_id_switch_risk_count"],
        "hidden_id_switch_risk_median": (
            float(median(hidden_id_switch_risks)) if hidden_id_switch_risks else None
        ),
        "na_by_reason": dict(sorted(na_by_reason.items())),
        "display_state_counts": dict(sorted(display_state_counts.items())),
        "speed_source_counts": dict(sorted(source_counts.items())),
        "contact_state_counts": dict(sorted(contact_state_counts.items())),
        "geometry_reason_counts": dict(sorted(geometry_reason_counts.items())),
        "fixed_lag_backfill_count": counts["fixed_lag_backfill_count"],
        "fixed_lag_ratio": counts["fixed_lag_backfill_count"] / total if total else 0.0,
        "speed_jump_p95_kmh": _p95(speed_jumps),
        "max_pedestrian_speed_kmh": max_speed if displayable else None,
        "pedestrian_max_speed_kmh": pedestrian_max_speed_kmh,
        "clip_acceptance_min_coverage": clip_acceptance_min_coverage,
        "displayed_high_uncertainty_max_ratio": DISPLAYED_HIGH_UNCERTAINTY_MAX_RATIO,
        "displayed_low_confidence_max_ratio": DISPLAYED_LOW_CONFIDENCE_MAX_RATIO,
        "model_references": [
            "homography_bev_ground_contact_speed",
            "ocsort_observation_centric_short_gap_recovery",
            "pedestrian_head_foot_scale_drift_v1",
            "joint_physics_posterior_v5",
        ],
        "passes_pedestrian_speed_acceptance": (
            coverage is not None
            and coverage >= clip_acceptance_min_coverage
            and counts["displayed_speed_limit_violation_count"] == 0
            and counts["displayed_id_switch_risk_count"] == 0
            and high_ratio <= DISPLAYED_HIGH_UNCERTAINTY_MAX_RATIO
            and low_ratio <= DISPLAYED_LOW_CONFIDENCE_MAX_RATIO
        ),
    }


def build_representative_speed_benchmark(
    payload: dict[str, Any],
) -> dict[str, Any]:
    regression_set = payload.get("regression_set")
    regression_set = regression_set if isinstance(regression_set, dict) else {}
    results = [
        result
        for result in payload.get("results", [])
        if isinstance(result, dict) and result.get("status") == "ok"
    ]
    role_map = _role_map(regression_set)
    vehicle_results = _results_for_role(results, role_map, VEHICLE_SPEED_ROLE)
    pedestrian_results = _results_for_role(results, role_map, PEDESTRIAN_SPEED_ROLE)
    target_vehicle_clips = _target_clips_for_role(
        regression_set,
        role_map,
        VEHICLE_SPEED_ROLE,
        vehicle_results,
    )
    target_pedestrian_clips = _target_clips_for_role(
        regression_set,
        role_map,
        PEDESTRIAN_SPEED_ROLE,
        pedestrian_results,
    )
    vehicle_aggregate = build_vehicle_speed_aggregate(
        vehicle_results,
        dense_city_acceptance_min_coverage=float(
            regression_set.get("aggregate_min_coverage", 0.993),
        ),
        clip_acceptance_min_coverage=float(regression_set.get("clip_min_coverage", 0.995)),
        car_hard_max_kmh=float(regression_set.get("max_car_speed_kmh", 160.0)),
    )
    pedestrian_audits = [
        _pedestrian_audit_for_result(
            result,
            clip_acceptance_min_coverage=float(
                regression_set.get(
                    "pedestrian_clip_min_coverage",
                    PEDESTRIAN_ACCEPTANCE_MIN_COVERAGE,
                ),
            ),
            pedestrian_max_speed_kmh=float(
                regression_set.get("pedestrian_max_speed_kmh", PEDESTRIAN_MAX_SPEED_KMH),
            ),
        )
        for result in pedestrian_results
    ]
    pedestrian_aggregate = _build_pedestrian_aggregate(
        pedestrian_audits,
        acceptance_min_coverage=float(
            regression_set.get(
                "pedestrian_clip_min_coverage",
                PEDESTRIAN_ACCEPTANCE_MIN_COVERAGE,
            ),
        ),
    )
    vehicle_rows = [
        row
        for row in vehicle_aggregate.get("clip_rows", [])
        if int(row.get("vehicle_track_samples") or 0) > 0
    ]
    pedestrian_rows = [
        audit
        for audit in pedestrian_audits
        if int(audit.get("pedestrian_track_samples") or 0) > 0
    ]
    vehicle_row_clips = {str(row.get("clip") or "") for row in vehicle_rows}
    pedestrian_row_clips = {str(row.get("clip") or "") for row in pedestrian_rows}
    vehicle_targets_satisfied = all(
        clip in vehicle_row_clips for clip in target_vehicle_clips
    )
    pedestrian_targets_satisfied = all(
        clip in pedestrian_row_clips for clip in target_pedestrian_clips
    )
    return {
        "regression_set": regression_set,
        "missing_clips": payload.get("missing_clips", []),
        "total_successful_clips": len(results),
        "target_vehicle_clips": target_vehicle_clips,
        "target_pedestrian_clips": target_pedestrian_clips,
        "vehicle_speed_aggregate": vehicle_aggregate,
        "vehicle_clip_rows_evaluated": vehicle_rows,
        "pedestrian_speed_aggregate": pedestrian_aggregate,
        "pedestrian_clip_rows_evaluated": pedestrian_rows,
        "passes_representative_speed_acceptance": (
            bool(vehicle_rows)
            and bool(pedestrian_rows)
            and vehicle_targets_satisfied
            and pedestrian_targets_satisfied
            and all(bool(row.get("passes_vehicle_speed_acceptance")) for row in vehicle_rows)
            and all(
                bool(row.get("passes_pedestrian_speed_acceptance"))
                for row in pedestrian_rows
            )
            and bool(vehicle_aggregate.get("passes_dense_city_acceptance"))
            and bool(pedestrian_aggregate.get("passes_pedestrian_speed_acceptance"))
        ),
    }


def render_representative_markdown(summary: dict[str, Any]) -> str:
    vehicle = summary.get("vehicle_speed_aggregate") or {}
    pedestrian = summary.get("pedestrian_speed_aggregate") or {}
    lines = [
        "# Representative Speed Benchmark",
        "",
        f"- Successful clips: {summary.get('total_successful_clips', 0)}",
        (
            "- Representative acceptance: "
            f"{summary.get('passes_representative_speed_acceptance')}"
        ),
        "",
        "## Vehicle Gate",
        "",
        f"- Samples: {vehicle.get('vehicle_track_samples', 0)}",
        f"- Coverage: {_fmt(vehicle.get('vehicle_display_coverage'))}",
        f"- Acceptance coverage: {_fmt(vehicle.get('coverage_used_for_acceptance'))}",
        f"- Passed: {vehicle.get('passes_dense_city_acceptance')}",
        f"- Hard rejected displayed: {vehicle.get('hard_rejected_display_count', 0)}",
        f"- ID-switch risk displayed: {vehicle.get('displayed_id_switch_risk_count', 0)}",
        "",
        "## Pedestrian Gate",
        "",
        f"- Samples: {pedestrian.get('pedestrian_track_samples', 0)}",
        f"- Coverage: {_fmt(pedestrian.get('pedestrian_display_coverage'))}",
        f"- Passed: {pedestrian.get('passes_pedestrian_speed_acceptance')}",
        (
            "- Speed-limit violations displayed: "
            f"{pedestrian.get('displayed_speed_limit_violation_count', 0)}"
        ),
        f"- ID-switch risk displayed: {pedestrian.get('displayed_id_switch_risk_count', 0)}",
        f"- High uncertainty ratio: {_fmt(pedestrian.get('displayed_high_uncertainty_ratio'))}",
        f"- Low confidence ratio: {_fmt(pedestrian.get('displayed_low_confidence_ratio'))}",
        "",
        "## Vehicle Clips",
        "",
        (
            "| clip | coverage | pass | low conf | high unc | hard reject | id risk | max speed |"
        ),
        "|---|---:|---|---:|---:|---:|---:|---:|",
    ]
    for row in summary.get("vehicle_clip_rows_evaluated", []):
        max_speed = max(
            [float(value) for value in (row.get("max_speed_by_class") or {}).values()],
            default=0.0,
        )
        lines.append(
            "| "
            f"{row.get('clip')} | "
            f"{_fmt(row.get('coverage_used_for_acceptance'))} | "
            f"{row.get('passes_vehicle_speed_acceptance')} | "
            f"{_fmt(row.get('displayed_low_confidence_ratio'))} | "
            f"{_fmt(row.get('displayed_high_uncertainty_ratio'))} | "
            f"{row.get('hard_rejected_display_count', 0)} | "
            f"{row.get('displayed_id_switch_risk_count', 0)} | "
            f"{max_speed:.2f} |"
        )
    lines.extend(
        [
            "",
            "## Pedestrian Clips",
            "",
            (
                "| clip | coverage | pass | low conf | high unc | "
                "speed limit | id risk | max speed |"
            ),
            "|---|---:|---|---:|---:|---:|---:|---:|",
        ],
    )
    for row in summary.get("pedestrian_clip_rows_evaluated", []):
        lines.append(
            "| "
            f"{row.get('clip')} | "
            f"{_fmt(row.get('coverage_used_for_acceptance'))} | "
            f"{row.get('passes_pedestrian_speed_acceptance')} | "
            f"{_fmt(row.get('displayed_low_confidence_ratio'))} | "
            f"{_fmt(row.get('displayed_high_uncertainty_ratio'))} | "
            f"{row.get('displayed_speed_limit_violation_count', 0)} | "
            f"{row.get('displayed_id_switch_risk_count', 0)} | "
            f"{_fmt(row.get('max_pedestrian_speed_kmh'))} |"
        )
    lines.append("")
    return "\n".join(lines)


def _build_pedestrian_aggregate(
    audits: list[dict[str, Any]],
    *,
    acceptance_min_coverage: float = PEDESTRIAN_ACCEPTANCE_MIN_COVERAGE,
) -> dict[str, Any]:
    rows = [audit for audit in audits if int(audit.get("pedestrian_track_samples") or 0) > 0]
    total = sum(int(row.get("pedestrian_track_samples") or 0) for row in rows)
    displayable = sum(
        int(row.get("displayable_pedestrian_track_samples") or 0) for row in rows
    )
    high_uncertainty = sum(
        int(row.get("displayed_high_uncertainty_count") or 0) for row in rows
    )
    low_confidence = sum(
        int(row.get("displayed_low_confidence_count") or 0) for row in rows
    )
    coverage = displayable / total if total else None
    high_ratio = high_uncertainty / displayable if displayable else 0.0
    low_ratio = low_confidence / displayable if displayable else 0.0
    max_speed = max(
        [
            float(row["max_pedestrian_speed_kmh"])
            for row in rows
            if row.get("max_pedestrian_speed_kmh") is not None
        ],
        default=0.0,
    )
    return {
        "pedestrian_track_samples": total,
        "displayable_pedestrian_track_samples": displayable,
        "pedestrian_display_coverage": coverage,
        "coverage_used_for_acceptance": coverage,
        "displayed_low_confidence_count": low_confidence,
        "displayed_low_confidence_ratio": low_ratio,
        "displayed_high_uncertainty_count": high_uncertainty,
        "displayed_high_uncertainty_ratio": high_ratio,
        "displayed_id_switch_risk_count": sum(
            int(row.get("displayed_id_switch_risk_count") or 0) for row in rows
        ),
        "displayed_speed_limit_violation_count": sum(
            int(row.get("displayed_speed_limit_violation_count") or 0) for row in rows
        ),
        "displayed_residual_rejection_reason_count": sum(
            int(row.get("displayed_residual_rejection_reason_count") or 0)
            for row in rows
        ),
        "max_pedestrian_speed_kmh": max_speed if displayable else None,
        "clip_rows": rows,
        "clip_acceptance_min_coverage": acceptance_min_coverage,
        "passes_pedestrian_speed_acceptance": (
            coverage is not None
            and coverage >= acceptance_min_coverage
            and high_ratio <= DISPLAYED_HIGH_UNCERTAINTY_MAX_RATIO
            and low_ratio <= DISPLAYED_LOW_CONFIDENCE_MAX_RATIO
            and all(bool(row.get("passes_pedestrian_speed_acceptance")) for row in rows)
        ),
    }


def _role_map(regression_set: dict[str, Any]) -> dict[str, set[str]]:
    raw_roles = regression_set.get("target_speed_roles") or regression_set.get("clip_roles")
    if not isinstance(raw_roles, dict):
        return {}
    role_map: dict[str, set[str]] = {}
    for clip, roles in raw_roles.items():
        normalized = {_normalize_role(role) for role in _role_values(roles)}
        normalized.discard("")
        if normalized:
            role_map[str(clip)] = normalized
    return role_map


def _results_for_role(
    results: list[dict[str, Any]],
    role_map: dict[str, set[str]],
    role: str,
) -> list[dict[str, Any]]:
    if not role_map:
        return results
    return [
        result
        for result in results
        if role in role_map.get(str(result.get("clip") or ""), set())
    ]


def _target_clips_for_role(
    regression_set: dict[str, Any],
    role_map: dict[str, set[str]],
    role: str,
    role_results: list[dict[str, Any]],
) -> list[str]:
    if not role_map:
        return [str(result.get("clip") or "") for result in role_results]
    clip_order = [str(clip) for clip in regression_set.get("clips", [])]
    ordered = [clip for clip in clip_order if role in role_map.get(clip, set())]
    extras = [
        clip
        for clip, roles in role_map.items()
        if role in roles and clip not in set(ordered)
    ]
    return ordered + sorted(extras)


def _role_values(value: object) -> list[object]:
    if isinstance(value, list | tuple | set):
        return list(value)
    return [value]


def _normalize_role(value: object) -> str:
    role = str(value or "").strip().lower().replace("-", "_")
    if role in {"vehicle", "vehicles", "car", "cars"}:
        return VEHICLE_SPEED_ROLE
    if role in {"pedestrian", "pedestrians", "person", "people"}:
        return PEDESTRIAN_SPEED_ROLE
    return role


def _pedestrian_audit_for_result(
    result: dict[str, Any],
    *,
    clip_acceptance_min_coverage: float,
    pedestrian_max_speed_kmh: float,
) -> dict[str, Any]:
    existing = result.get("pedestrian_speed_audit")
    if isinstance(existing, dict):
        return existing
    frame_reports = result.get("frame_reports")
    frame_reports = frame_reports if isinstance(frame_reports, list) else []
    return build_pedestrian_speed_audit(
        frame_reports,
        clip=str(result.get("clip") or ""),
        clip_acceptance_min_coverage=clip_acceptance_min_coverage,
        pedestrian_max_speed_kmh=pedestrian_max_speed_kmh,
    )


def _is_pedestrian(track: dict[str, Any]) -> bool:
    return int(track.get("class_id", -1)) == PERSON_CLASS_ID or str(
        track.get("class_name") or "",
    ).lower() == "person"


def _is_displayable(track: dict[str, Any]) -> bool:
    return (
        track.get("speed_kmh") is not None
        and bool(track.get("physics_valid", False))
        and not bool(track.get("speed_display_hidden", False))
    )


def _is_low_confidence(track: dict[str, Any]) -> bool:
    value = _float_or_none(track.get("speed_confidence"))
    return value is not None and value < PEDESTRIAN_LOW_CONFIDENCE_THRESHOLD


def _is_high_uncertainty(track: dict[str, Any]) -> bool:
    uncertainty = _float_or_none(track.get("speed_uncertainty_kmh"))
    if uncertainty is None:
        return False
    speed = max(_float_or_none(track.get("speed_kmh")) or 0.0, 0.0)
    threshold = max(
        PEDESTRIAN_HIGH_UNCERTAINTY_BASE_KMH,
        speed * PEDESTRIAN_HIGH_UNCERTAINTY_SPEED_RATIO,
    )
    return uncertainty > threshold


def _id_switch_risk(track: dict[str, Any]) -> float:
    value = _float_or_none(track.get("id_switch_risk"))
    return max(0.0, min(1.0, value or 0.0))


def _display_state(track: dict[str, Any], displayable: bool) -> str:
    if displayable:
        if bool(track.get("fixed_lag_backfilled")) or bool(track.get("reconstructed")):
            return "fixed_lag_refined"
        return "measured"
    explicit = track.get("pedestrian_speed_display_state")
    if explicit:
        return str(explicit)
    if track.get("speed_kmh") is None:
        return "warming_up_hidden"
    return "rejected_hidden"


def _hidden_reason(track: dict[str, Any]) -> str:
    for key in (
        "pedestrian_speed_display_rejection_reason",
        "confidence_rejection_reason",
        "geometry_rejection_reason",
        "integrity_rejection_reason",
        "association_rejection_reason",
        "rejection_reason",
    ):
        value = track.get(key)
        if value:
            return str(value)
    return "speed_missing" if track.get("speed_kmh") is None else "physics_invalid"


def _has_residual_rejection_reason(track: dict[str, Any]) -> bool:
    return any(
        bool(track.get(key))
        for key in (
            "confidence_rejection_reason",
            "geometry_rejection_reason",
            "integrity_rejection_reason",
            "association_rejection_reason",
            "rejection_reason",
        )
    )


def _geometry_reason(track: dict[str, Any]) -> str | None:
    value = track.get("geometry_rejection_reason")
    if value:
        return str(value)
    diagnostics = track.get("speed_geometry_diagnostics")
    if isinstance(diagnostics, dict):
        value = diagnostics.get("pedestrian_metric_rejection_reason") or diagnostics.get(
            "plane_reason",
        )
        if value:
            return str(value)
    return None


def _speed_source(track: dict[str, Any]) -> str:
    return str(
        track.get("speed_source")
        or track.get("measurement_source")
        or track.get("contact_source")
        or "unknown",
    )


def _speed_jump_values(
    speeds_by_track: defaultdict[int, list[tuple[int, float, float]]],
) -> list[float]:
    values: list[float] = []
    for track_speeds in speeds_by_track.values():
        ordered = sorted(track_speeds, key=lambda item: item[0])
        for previous, current in zip(ordered, ordered[1:], strict=False):
            values.append(abs(current[2] - previous[2]))
    return values


def _frame_index(report: dict[str, Any], fallback: int) -> int:
    try:
        return int(report.get("frame_index", fallback))
    except (TypeError, ValueError):
        return fallback


def _timestamp_sec(report: dict[str, Any], frame_index: int) -> float:
    try:
        return float(report.get("timestamp_sec", frame_index / 30.0))
    except (TypeError, ValueError):
        return frame_index / 30.0


def _float_or_none(value: object) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int | float | str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _p95(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(round((len(ordered) - 1) * 0.95)))
    return float(ordered[index])


def _fmt(value: object) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)
