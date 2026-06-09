from __future__ import annotations

import subprocess
from collections import Counter, defaultdict
from csv import DictReader
from pathlib import Path
from statistics import mean, median, pstdev
from typing import Any

VEHICLE_CLASS_IDS = {2, 3, 5, 7}
VEHICLE_SPEED_REPORT_SCHEMA_VERSION = "vehicle_speed_report_v3"
FROZEN_LAST_VALID_WINDOW_FRAMES = 15
RECONSTRUCTED_SPEED_MAX_UNCERTAINTY_KMH = 30.0
RECONSTRUCTED_SPEED_MIN_CONFIDENCE = 0.05
DISPLAYED_HIGH_UNCERTAINTY_MAX_RATIO = 0.02
DISPLAYED_LOW_CONFIDENCE_MAX_RATIO = 0.03
HIGH_UNCERTAINTY_KMH = 25.0
HIGH_INTERVAL_WIDTH_KMH = 30.0
LOW_CONFIDENCE_THRESHOLD = 0.15
BBOX_CENTER_FALLBACK_MAX_CONFIDENCE = LOW_CONFIDENCE_THRESHOLD - 0.01
BBOX_CENTER_FALLBACK_MIN_UNCERTAINTY_KMH = HIGH_UNCERTAINTY_KMH + 1.0
ID_SWITCH_DISPLAY_THRESHOLD = 0.7
RTS_RECALIBRATION_MIN_TRACK_SAMPLES = 6
RTS_RECALIBRATION_MAX_SPEED_JUMP_KMH = 8.0
RTS_RECALIBRATION_MAX_ACCEL_MPS2 = 5.0
RTS_RECALIBRATION_MAX_JERK_MPS3 = 120.0
RTS_RECALIBRATION_MIN_CONTACT_QUALITY = 0.25
RTS_RECALIBRATION_MIN_CONFIDENCE = 0.35
RTS_RECALIBRATION_MAX_UNCERTAINTY_KMH = 7.0
RTS_RECALIBRATION_INTERVAL_SIGMA = 1.96
ID_SWITCH_POSTERIOR_RISK = 0.55
ID_SWITCH_POSTERIOR_MIN_CONFIDENCE = 0.35
ID_SWITCH_POSTERIOR_MIN_UNCERTAINTY_KMH = 3.0
HARD_REJECTION_REASONS = {
    "class_speed_limit",
    "hard_speed_limit",
    "mahalanobis_gate",
    "id_switch_gate",
    "tracking_integrity",
}
DENSE_CITY_ACCEPTANCE_MIN_COVERAGE = 0.993
CLIP_ACCEPTANCE_MIN_COVERAGE = 0.995
CAR_HARD_MAX_KMH = 160.0
VEHICLE_WIDTH_PRIOR_M = {
    "car": 1.85,
    "bus": 2.55,
    "truck": 2.55,
    "motorcycle": 0.8,
}


def source_commit(cwd: Path | None = None) -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    value = result.stdout.strip()
    return value or None


def annotate_vehicle_speed_reports(
    frame_reports: list[dict[str, Any]],
    *,
    reconstruction_applied: bool,
    source_commit_value: str | None = None,
    freeze_window_frames: int = FROZEN_LAST_VALID_WINDOW_FRAMES,
) -> list[dict[str, Any]]:
    last_valid: dict[tuple[int, int], dict[str, Any]] = {}
    for fallback_index, report in enumerate(frame_reports):
        frame_index = _frame_index(report, fallback_index)
        report["report_schema_version"] = VEHICLE_SPEED_REPORT_SCHEMA_VERSION
        report["reconstruction_applied"] = bool(reconstruction_applied)
        if source_commit_value is not None:
            report["source_commit"] = source_commit_value
        for track in report.get("active_tracks", []):
            if not isinstance(track, dict) or not _is_vehicle(track):
                continue
            _annotate_contact_quality(track)
            key = (int(track.get("tracker_id", -1)), int(track.get("class_id", -1)))
            if _should_hide_displayable_vehicle_speed(track):
                track["physics_valid"] = False
                track["vehicle_speed_display_state"] = "rejected_hidden"
                track["speed_display_hidden"] = True
                continue
            if _is_displayable(track):
                state = (
                    "fixed_lag_refined"
                    if bool(track.get("fixed_lag_backfilled"))
                    or str(track.get("speed_source") or "").startswith("fixed_lag")
                    else "measured"
                )
                track["vehicle_speed_display_state"] = state
                track["speed_display_hidden"] = False
                last_valid[key] = {
                    "frame_index": frame_index,
                    "speed_kmh": float(track["speed_kmh"]),
                    "speed_uncertainty_kmh": track.get("speed_uncertainty_kmh"),
                    "speed_confidence": track.get("speed_confidence"),
                    "speed_confidence_interval_kmh": track.get(
                        "speed_confidence_interval_kmh",
                    ),
                }
                continue

            if _can_admit_reconstructed_vehicle_speed(track):
                track["physics_valid"] = True
                track["vehicle_speed_display_state"] = "fixed_lag_refined"
                track["speed_display_hidden"] = False
                track["vehicle_speed_recovered_from_unstable_observation"] = True
                last_valid[key] = {
                    "frame_index": frame_index,
                    "speed_kmh": float(track["speed_kmh"]),
                    "speed_uncertainty_kmh": track.get("speed_uncertainty_kmh"),
                    "speed_confidence": track.get("speed_confidence"),
                    "speed_confidence_interval_kmh": track.get(
                        "speed_confidence_interval_kmh",
                    ),
                }
                continue

            previous = last_valid.get(key)
            if _can_freeze(track, previous, frame_index, freeze_window_frames):
                track["speed_kmh"] = previous["speed_kmh"]
                track["speed_uncertainty_kmh"] = previous.get("speed_uncertainty_kmh")
                track["speed_confidence"] = previous.get("speed_confidence")
                track["speed_confidence_interval_kmh"] = previous.get(
                    "speed_confidence_interval_kmh",
                )
                track["physics_valid"] = True
                track["speed_frozen"] = True
                track["speed_source"] = "frozen_last_valid"
                track["vehicle_speed_display_state"] = "frozen_last_valid"
                track["speed_display_hidden"] = False
                continue

            track["vehicle_speed_display_state"] = (
                "warming_up_hidden" if _is_warming_up(track) else "rejected_hidden"
            )
            track["speed_display_hidden"] = True
    _backfill_vehicle_warmup_speeds(frame_reports, freeze_window_frames)
    _recalibrate_stable_fixed_lag_rts_speeds(frame_reports)
    _downgrade_stable_world_jump_id_switch_risks(frame_reports)
    return frame_reports


def build_vehicle_speed_audit(
    frame_reports: list[dict[str, Any]],
    *,
    clip: str | None = None,
    processed_video_path: str | None = None,
    source_commit_value: str | None = None,
    speed_ground_truth_dir: Path | None = None,
) -> dict[str, Any]:
    counts: Counter[str] = Counter()
    na_by_reason: Counter[str] = Counter()
    physics_invalid_by_reason: Counter[str] = Counter()
    display_state_counts: Counter[str] = Counter()
    contact_source_counts: Counter[str] = Counter()
    dominant_error_source_counts: Counter[str] = Counter()
    hidden_id_switch_by_class: Counter[str] = Counter()
    hidden_id_switch_by_source: Counter[str] = Counter()
    hidden_id_switch_by_state: Counter[str] = Counter()
    hidden_id_switch_risks: list[float] = []
    hidden_id_switch_trackers: set[tuple[int, int]] = set()
    max_speed_by_class: dict[str, float] = {}
    speed_jump_values: list[float] = []
    acceleration_values: list[float] = []
    jerk_values: list[float] = []
    speeds_by_track: defaultdict[tuple[int, int], list[tuple[int, float, float]]] = (
        defaultdict(list)
    )
    frozen_runs_by_track: defaultdict[tuple[int, int], int] = defaultdict(int)
    max_consecutive_frozen_frames = 0

    for fallback_index, report in enumerate(frame_reports):
        frame_index = _frame_index(report, fallback_index)
        timestamp = _timestamp_sec(report, frame_index)
        for track in report.get("active_tracks", []):
            if not isinstance(track, dict) or not _is_vehicle(track):
                continue
            counts["vehicle_track_samples"] += 1
            safe_sample = _is_safe_vehicle_sample(track)
            if safe_sample:
                counts["safe_vehicle_track_samples"] += 1
            else:
                counts["unsafe_vehicle_track_samples"] += 1
            display_state = str(track.get("vehicle_speed_display_state") or "unknown")
            display_state_counts[display_state] += 1
            key = (int(track.get("tracker_id", -1)), int(track.get("class_id", -1)))
            contact_source = str(track.get("contact_point_source") or "unknown")
            contact_source_counts[contact_source] += 1
            dominant_source = str(
                track.get("contact_point_dominant_error_source") or "unknown",
            )
            dominant_error_source_counts[dominant_source] += 1
            if bool(track.get("bbox_center_fallback")):
                counts["bbox_center_fallback_count"] += 1
            if _is_fixed_lag_reconstructed(track):
                counts["fixed_lag_backfill_count"] += 1
            if bool(track.get("speed_uncertainty_recalibrated")):
                counts["speed_uncertainty_recalibrated_count"] += 1
            if (
                track.get("speed_source") == "frozen_last_valid"
                or track.get("vehicle_speed_display_state") == "frozen_last_valid"
            ):
                counts["frozen_last_valid_count"] += 1
                frozen_runs_by_track[key] += 1
                max_consecutive_frozen_frames = max(
                    max_consecutive_frozen_frames,
                    frozen_runs_by_track[key],
                )
            else:
                frozen_runs_by_track[key] = 0

            if _is_displayable(track):
                counts["displayable_vehicle_track_samples"] += 1
                if safe_sample:
                    counts["safe_displayable_vehicle_track_samples"] += 1
                if _is_low_confidence(track):
                    counts["displayed_low_confidence_count"] += 1
                if _is_high_uncertainty(track):
                    counts["displayed_high_uncertainty_count"] += 1
                if _id_switch_risk(track) >= ID_SWITCH_DISPLAY_THRESHOLD:
                    counts["displayed_id_switch_risk_count"] += 1
                if _is_hard_rejected(track):
                    counts["hard_rejected_display_count"] += 1
                speed = float(track["speed_kmh"])
                class_key = str(track.get("class_name") or track.get("class_id"))
                max_speed_by_class[class_key] = max(
                    max_speed_by_class.get(class_key, 0.0),
                    speed,
                )
                speeds_by_track[key].append((frame_index, timestamp, speed))
                _append_float(speed_jump_values, track.get("speed_jump_p95_kmh"))
                _append_abs_float(acceleration_values, track.get("acceleration_mps2"))
                _append_abs_float(acceleration_values, track.get("acceleration_p95_mps2"))
                _append_abs_float(jerk_values, track.get("jerk_p95_mps3"))
                continue

            id_risk = _id_switch_risk(track)
            if id_risk >= ID_SWITCH_DISPLAY_THRESHOLD:
                counts["hidden_id_switch_risk_count"] += 1
                hidden_id_switch_risks.append(id_risk)
                hidden_id_switch_trackers.add(key)
                class_key = str(track.get("class_name") or track.get("class_id"))
                hidden_id_switch_by_class[class_key] += 1
                hidden_id_switch_by_source[str(track.get("speed_source") or "unknown")] += 1
                hidden_id_switch_by_state[display_state] += 1
            if track.get("speed_kmh") is None and _is_warming_up(track):
                counts["unresolved_warmup_hidden_count"] += 1
            reason = _invalid_reason(track)
            na_by_reason[reason] += 1
            if track.get("speed_kmh") is not None and not bool(track.get("physics_valid", False)):
                physics_invalid_by_reason[reason] += 1

    for track_speeds in speeds_by_track.values():
        ordered = sorted(track_speeds, key=lambda item: item[0])
        for previous, current in zip(ordered, ordered[1:], strict=False):
            speed_jump_values.append(abs(current[2] - previous[2]))
        for left, middle, right in zip(ordered, ordered[1:], ordered[2:], strict=False):
            dt_left = max(middle[1] - left[1], 1e-6)
            dt_right = max(right[1] - middle[1], 1e-6)
            accel_left = ((middle[2] - left[2]) / 3.6) / dt_left
            accel_right = ((right[2] - middle[2]) / 3.6) / dt_right
            acceleration_values.extend([abs(accel_left), abs(accel_right)])
            jerk_values.append(abs(accel_right - accel_left) / max(dt_right, 1e-6))

    total = counts["vehicle_track_samples"]
    displayable = counts["displayable_vehicle_track_samples"]
    safe_total = counts["safe_vehicle_track_samples"]
    safe_displayable = counts["safe_displayable_vehicle_track_samples"]
    frozen_count = counts["frozen_last_valid_count"]
    fixed_lag_count = counts["fixed_lag_backfill_count"]
    displayed_low_confidence_count = counts["displayed_low_confidence_count"]
    displayed_high_uncertainty_count = counts["displayed_high_uncertainty_count"]
    return {
        "clip": clip,
        "processed_video_path": processed_video_path,
        "report_schema_version": VEHICLE_SPEED_REPORT_SCHEMA_VERSION,
        "reconstruction_applied": any(
            bool(report.get("reconstruction_applied")) for report in frame_reports
        ),
        "source_commit": source_commit_value
        or next(
            (
                str(report.get("source_commit"))
                for report in frame_reports
                if report.get("source_commit")
            ),
            None,
        ),
        "vehicle_track_samples": total,
        "displayable_vehicle_track_samples": displayable,
        "vehicle_display_coverage": displayable / total if total else None,
        "safe_vehicle_track_samples": safe_total,
        "safe_displayable_vehicle_track_samples": safe_displayable,
        "safe_vehicle_display_coverage": (
            safe_displayable / safe_total if safe_total else None
        ),
        "unsafe_vehicle_track_samples": counts["unsafe_vehicle_track_samples"],
        "displayed_low_confidence_count": displayed_low_confidence_count,
        "displayed_low_confidence_ratio": (
            displayed_low_confidence_count / displayable if displayable else 0.0
        ),
        "displayed_high_uncertainty_count": displayed_high_uncertainty_count,
        "displayed_high_uncertainty_ratio": (
            displayed_high_uncertainty_count / displayable if displayable else 0.0
        ),
        "hard_rejected_display_count": counts["hard_rejected_display_count"],
        "displayed_id_switch_risk_count": counts["displayed_id_switch_risk_count"],
        "na_by_reason": dict(sorted(na_by_reason.items())),
        "physics_invalid_by_reason": dict(sorted(physics_invalid_by_reason.items())),
        "fixed_lag_backfill_count": fixed_lag_count,
        "fixed_lag_ratio": fixed_lag_count / total if total else 0.0,
        "speed_uncertainty_recalibrated_count": counts[
            "speed_uncertainty_recalibrated_count"
        ],
        "frozen_last_valid_count": frozen_count,
        "frozen_ratio": frozen_count / total if total else 0.0,
        "max_consecutive_frozen_frames": max_consecutive_frozen_frames,
        "speed_jump_p95_kmh": _p95(speed_jump_values),
        "acceleration_p95_mps2": _p95(acceleration_values),
        "jerk_p95_mps3": _p95(jerk_values),
        "max_speed_by_class": dict(sorted(max_speed_by_class.items())),
        "vehicle_speed_display_state_counts": dict(sorted(display_state_counts.items())),
        "contact_point_source_counts": dict(sorted(contact_source_counts.items())),
        "contact_point_dominant_error_source_counts": dict(
            sorted(dominant_error_source_counts.items()),
        ),
        "bbox_center_fallback_count": counts["bbox_center_fallback_count"],
        "unresolved_warmup_hidden_count": counts["unresolved_warmup_hidden_count"],
        "id_switch_risk_diagnostics": {
            "hidden_count": counts["hidden_id_switch_risk_count"],
            "hidden_tracker_count": len(hidden_id_switch_trackers),
            "hidden_by_class": dict(sorted(hidden_id_switch_by_class.items())),
            "hidden_by_speed_source": dict(sorted(hidden_id_switch_by_source.items())),
            "hidden_by_display_state": dict(sorted(hidden_id_switch_by_state.items())),
            "median_hidden_risk": (
                float(median(hidden_id_switch_risks))
                if hidden_id_switch_risks
                else None
            ),
            "max_hidden_risk": max(hidden_id_switch_risks, default=None),
            "recommended_next_step": (
                "review_bev_tracklet_reassociation"
                if hidden_id_switch_risks
                else "none"
            ),
        },
        "vehicle_3d_scale_sanity": build_vehicle_3d_scale_sanity(frame_reports),
        "speed_ground_truth_metrics": build_speed_ground_truth_metrics(
            frame_reports,
            clip=clip,
            speed_ground_truth_dir=speed_ground_truth_dir,
        ),
    }


def build_vehicle_speed_aggregate(
    results: list[dict[str, Any]],
    *,
    dense_city_acceptance_min_coverage: float = DENSE_CITY_ACCEPTANCE_MIN_COVERAGE,
    clip_acceptance_min_coverage: float = CLIP_ACCEPTANCE_MIN_COVERAGE,
    car_hard_max_kmh: float = CAR_HARD_MAX_KMH,
) -> dict[str, Any]:
    clip_rows: list[dict[str, Any]] = []
    total_samples = 0
    total_displayable = 0
    total_safe_samples = 0
    total_safe_displayable = 0
    aggregate_na: Counter[str] = Counter()
    aggregate_invalid: Counter[str] = Counter()
    aggregate_hidden_id_switch_by_class: Counter[str] = Counter()
    aggregate_hidden_id_switch_by_source: Counter[str] = Counter()
    aggregate_hidden_id_switch_by_state: Counter[str] = Counter()
    aggregate_3d_region_quality: Counter[str] = Counter()
    max_speed_by_class: dict[str, float] = {}
    speed_jump_values: list[float] = []
    acceleration_values: list[float] = []
    jerk_values: list[float] = []
    homography_uncertainty_multipliers: list[float] = []
    aggregate_counts: Counter[str] = Counter()
    safe_schema_seen = False

    for result in results:
        if result.get("status") not in {None, "ok"}:
            continue
        audit = result.get("vehicle_speed_audit")
        if not isinstance(audit, dict):
            continue
        samples = _int_or_default(audit.get("vehicle_track_samples"), 0)
        displayable = _int_or_default(
            audit.get("displayable_vehicle_track_samples"),
            0,
        )
        has_safe_samples = "safe_vehicle_track_samples" in audit
        has_safe_displayable = "safe_displayable_vehicle_track_samples" in audit
        safe_schema_seen = (
            safe_schema_seen
            or has_safe_samples
            or has_safe_displayable
            or "safe_vehicle_display_coverage" in audit
        )
        safe_samples = _int_or_default(
            audit.get("safe_vehicle_track_samples"),
            samples,
        ) if has_safe_samples else samples
        safe_displayable = _int_or_default(
            audit.get("safe_displayable_vehicle_track_samples"),
            displayable,
        ) if has_safe_displayable else displayable
        coverage = audit.get("vehicle_display_coverage")
        safe_coverage = audit.get("safe_vehicle_display_coverage")
        if safe_coverage is None and safe_samples:
            safe_coverage = safe_displayable / safe_samples
        total_samples += samples
        total_displayable += displayable
        total_safe_samples += safe_samples
        total_safe_displayable += safe_displayable
        _update_counter(aggregate_na, audit.get("na_by_reason"))
        _update_counter(aggregate_invalid, audit.get("physics_invalid_by_reason"))
        id_switch_diagnostics = audit.get("id_switch_risk_diagnostics")
        if isinstance(id_switch_diagnostics, dict):
            _update_counter(
                aggregate_hidden_id_switch_by_class,
                id_switch_diagnostics.get("hidden_by_class"),
            )
            _update_counter(
                aggregate_hidden_id_switch_by_source,
                id_switch_diagnostics.get("hidden_by_speed_source"),
            )
            _update_counter(
                aggregate_hidden_id_switch_by_state,
                id_switch_diagnostics.get("hidden_by_display_state"),
            )
        _merge_max_speed(max_speed_by_class, audit.get("max_speed_by_class"))
        _append_float(speed_jump_values, audit.get("speed_jump_p95_kmh"))
        _append_float(acceleration_values, audit.get("acceleration_p95_mps2"))
        _append_float(jerk_values, audit.get("jerk_p95_mps3"))
        scale_sanity = audit.get("vehicle_3d_scale_sanity")
        if isinstance(scale_sanity, dict):
            if bool(scale_sanity.get("available")):
                aggregate_counts["vehicle_3d_scale_sanity_available_count"] += 1
            quality = str(scale_sanity.get("calibration_region_quality") or "unknown")
            aggregate_3d_region_quality[quality] += 1
            if quality in {"review", "poor"}:
                aggregate_counts["vehicle_3d_review_clip_count"] += 1
            _append_float(
                homography_uncertainty_multipliers,
                scale_sanity.get("homography_uncertainty_multiplier"),
            )
        else:
            aggregate_3d_region_quality["missing"] += 1
        for key in (
            "displayed_low_confidence_count",
            "displayed_high_uncertainty_count",
            "hard_rejected_display_count",
            "displayed_id_switch_risk_count",
            "fixed_lag_backfill_count",
            "speed_uncertainty_recalibrated_count",
            "frozen_last_valid_count",
            "bbox_center_fallback_count",
            "unsafe_vehicle_track_samples",
            "unresolved_warmup_hidden_count",
        ):
            aggregate_counts[key] += int(audit.get(key) or 0)
        if isinstance(id_switch_diagnostics, dict):
            aggregate_counts["hidden_id_switch_risk_count"] += int(
                id_switch_diagnostics.get("hidden_count") or 0,
            )
        max_car_speed = _max_vehicle_speed(audit)
        gate_coverage = _coverage_for_gate(audit)
        clip_rows.append(
            {
                "clip": audit.get("clip") or result.get("clip"),
                "vehicle_track_samples": samples,
                "displayable_vehicle_track_samples": displayable,
                "vehicle_display_coverage": coverage,
                "safe_vehicle_track_samples": safe_samples,
                "safe_displayable_vehicle_track_samples": safe_displayable,
                "safe_vehicle_display_coverage": safe_coverage,
                "coverage_used_for_acceptance": gate_coverage,
                "na_by_reason": audit.get("na_by_reason") or {},
                "physics_invalid_by_reason": audit.get("physics_invalid_by_reason") or {},
                "fixed_lag_backfill_count": int(audit.get("fixed_lag_backfill_count") or 0),
                "fixed_lag_ratio": float(audit.get("fixed_lag_ratio") or 0.0),
                "speed_uncertainty_recalibrated_count": int(
                    audit.get("speed_uncertainty_recalibrated_count") or 0,
                ),
                "frozen_last_valid_count": int(audit.get("frozen_last_valid_count") or 0),
                "frozen_ratio": float(audit.get("frozen_ratio") or 0.0),
                "max_consecutive_frozen_frames": int(
                    audit.get("max_consecutive_frozen_frames") or 0,
                ),
                "displayed_low_confidence_ratio": float(
                    audit.get("displayed_low_confidence_ratio") or 0.0,
                ),
                "displayed_high_uncertainty_ratio": float(
                    audit.get("displayed_high_uncertainty_ratio") or 0.0,
                ),
                "hard_rejected_display_count": int(
                    audit.get("hard_rejected_display_count") or 0,
                ),
                "displayed_id_switch_risk_count": int(
                    audit.get("displayed_id_switch_risk_count") or 0,
                ),
                "hidden_id_switch_risk_count": int(
                    (audit.get("id_switch_risk_diagnostics") or {}).get("hidden_count")
                    if isinstance(audit.get("id_switch_risk_diagnostics"), dict)
                    else 0,
                ),
                "unresolved_warmup_hidden_count": int(
                    audit.get("unresolved_warmup_hidden_count") or 0,
                ),
                "speed_jump_p95_kmh": audit.get("speed_jump_p95_kmh"),
                "acceleration_p95_mps2": audit.get("acceleration_p95_mps2"),
                "jerk_p95_mps3": audit.get("jerk_p95_mps3"),
                "max_speed_by_class": audit.get("max_speed_by_class") or {},
                "vehicle_3d_calibration_region_quality": (
                    scale_sanity.get("calibration_region_quality")
                    if isinstance(scale_sanity, dict)
                    else None
                ),
                "vehicle_3d_homography_uncertainty_multiplier": (
                    scale_sanity.get("homography_uncertainty_multiplier")
                    if isinstance(scale_sanity, dict)
                    else None
                ),
                "passes_vehicle_speed_acceptance": (
                    gate_coverage is not None
                    and float(gate_coverage) >= clip_acceptance_min_coverage
                    and max_car_speed <= car_hard_max_kmh
                    and _passes_quality_gate(audit)
                ),
            },
        )

    aggregate_coverage = total_displayable / total_samples if total_samples else None
    aggregate_safe_coverage = (
        total_safe_displayable / total_safe_samples if total_safe_samples else None
    )
    displayed_low_ratio = (
        aggregate_counts["displayed_low_confidence_count"] / total_displayable
        if total_displayable
        else 0.0
    )
    displayed_high_uncertainty_ratio = (
        aggregate_counts["displayed_high_uncertainty_count"] / total_displayable
        if total_displayable
        else 0.0
    )
    max_consecutive_frozen_frames = max(
        (int(row["max_consecutive_frozen_frames"]) for row in clip_rows),
        default=0,
    )
    aggregate_gate_coverage = _combined_gate_coverage(
        aggregate_coverage,
        aggregate_safe_coverage,
        safe_schema_seen=safe_schema_seen,
    )
    return {
        "vehicle_track_samples": total_samples,
        "displayable_vehicle_track_samples": total_displayable,
        "vehicle_display_coverage": aggregate_coverage,
        "safe_vehicle_track_samples": total_safe_samples,
        "safe_displayable_vehicle_track_samples": total_safe_displayable,
        "safe_vehicle_display_coverage": aggregate_safe_coverage,
        "unsafe_vehicle_track_samples": aggregate_counts["unsafe_vehicle_track_samples"],
        "coverage_used_for_acceptance": aggregate_gate_coverage,
        "na_by_reason": dict(sorted(aggregate_na.items())),
        "physics_invalid_by_reason": dict(sorted(aggregate_invalid.items())),
        "displayed_low_confidence_count": aggregate_counts[
            "displayed_low_confidence_count"
        ],
        "displayed_low_confidence_ratio": displayed_low_ratio,
        "displayed_high_uncertainty_count": aggregate_counts[
            "displayed_high_uncertainty_count"
        ],
        "displayed_high_uncertainty_ratio": displayed_high_uncertainty_ratio,
        "hard_rejected_display_count": aggregate_counts["hard_rejected_display_count"],
        "displayed_id_switch_risk_count": aggregate_counts[
            "displayed_id_switch_risk_count"
        ],
        "hidden_id_switch_risk_count": aggregate_counts["hidden_id_switch_risk_count"],
        "unresolved_warmup_hidden_count": aggregate_counts[
            "unresolved_warmup_hidden_count"
        ],
        "hidden_id_switch_risk_by_class": dict(
            sorted(aggregate_hidden_id_switch_by_class.items()),
        ),
        "hidden_id_switch_risk_by_speed_source": dict(
            sorted(aggregate_hidden_id_switch_by_source.items()),
        ),
        "hidden_id_switch_risk_by_display_state": dict(
            sorted(aggregate_hidden_id_switch_by_state.items()),
        ),
        "fixed_lag_backfill_count": aggregate_counts["fixed_lag_backfill_count"],
        "fixed_lag_ratio": (
            aggregate_counts["fixed_lag_backfill_count"] / total_samples
            if total_samples
            else 0.0
        ),
        "speed_uncertainty_recalibrated_count": aggregate_counts[
            "speed_uncertainty_recalibrated_count"
        ],
        "frozen_last_valid_count": aggregate_counts["frozen_last_valid_count"],
        "frozen_ratio": (
            aggregate_counts["frozen_last_valid_count"] / total_samples
            if total_samples
            else 0.0
        ),
        "max_consecutive_frozen_frames": max_consecutive_frozen_frames,
        "bbox_center_fallback_count": aggregate_counts["bbox_center_fallback_count"],
        "vehicle_3d_scale_sanity_available_count": aggregate_counts[
            "vehicle_3d_scale_sanity_available_count"
        ],
        "vehicle_3d_review_clip_count": aggregate_counts["vehicle_3d_review_clip_count"],
        "vehicle_3d_calibration_region_quality_counts": dict(
            sorted(aggregate_3d_region_quality.items()),
        ),
        "vehicle_3d_homography_uncertainty_multiplier_p95": _p95(
            homography_uncertainty_multipliers,
        ),
        "speed_jump_p95_kmh": _p95(speed_jump_values),
        "acceleration_p95_mps2": _p95(acceleration_values),
        "jerk_p95_mps3": _p95(jerk_values),
        "max_speed_by_class": dict(sorted(max_speed_by_class.items())),
        "clip_rows": clip_rows,
        "dense_city_acceptance_min_coverage": dense_city_acceptance_min_coverage,
        "clip_acceptance_min_coverage": clip_acceptance_min_coverage,
        "displayed_high_uncertainty_max_ratio": DISPLAYED_HIGH_UNCERTAINTY_MAX_RATIO,
        "displayed_low_confidence_max_ratio": DISPLAYED_LOW_CONFIDENCE_MAX_RATIO,
        "max_consecutive_frozen_frame_limit": FROZEN_LAST_VALID_WINDOW_FRAMES,
        "passes_dense_city_acceptance": (
            aggregate_gate_coverage is not None
            and aggregate_gate_coverage >= dense_city_acceptance_min_coverage
            and _max_speed_from_mapping(max_speed_by_class) <= car_hard_max_kmh
            and aggregate_counts["hard_rejected_display_count"] == 0
            and aggregate_counts["displayed_id_switch_risk_count"] == 0
            and displayed_high_uncertainty_ratio <= DISPLAYED_HIGH_UNCERTAINTY_MAX_RATIO
            and displayed_low_ratio <= DISPLAYED_LOW_CONFIDENCE_MAX_RATIO
            and max_consecutive_frozen_frames <= FROZEN_LAST_VALID_WINDOW_FRAMES
        ),
    }


def processed_video_needs_regeneration(
    processed_video_path: Path | None,
    *,
    source_commit_value: str | None = None,
) -> bool:
    if processed_video_path is None:
        return False
    audit_path = processed_video_path.with_name(
        f"{processed_video_path.stem}_speed_audit.json",
    )
    if not processed_video_path.exists() or not audit_path.exists():
        return True
    try:
        import json

        audit = json.loads(audit_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return True
    if audit.get("report_schema_version") != VEHICLE_SPEED_REPORT_SCHEMA_VERSION:
        return True
    if audit.get("reconstruction_applied") is not True:
        return True
    if source_commit_value is not None and audit.get("source_commit") != source_commit_value:
        return True
    return False


def write_vehicle_speed_audit(
    frame_reports: list[dict[str, Any]],
    *,
    clip: str,
    processed_video_path: Path | None,
    diagnostics_dir: Path | None,
    source_commit_value: str | None = None,
    regenerated_due_to_stale_audit: bool = False,
    speed_ground_truth_dir: Path | None = None,
) -> dict[str, Any]:
    audit = build_vehicle_speed_audit(
        frame_reports,
        clip=clip,
        processed_video_path=str(processed_video_path) if processed_video_path else None,
        source_commit_value=source_commit_value,
        speed_ground_truth_dir=speed_ground_truth_dir,
    )
    audit["regenerated_due_to_stale_audit"] = regenerated_due_to_stale_audit
    audit_path = None
    diagnostics_path = None
    if processed_video_path is not None:
        audit_path = processed_video_path.with_name(
            f"{processed_video_path.stem}_speed_audit.json",
        )
        audit["speed_audit_path"] = str(audit_path)
    if diagnostics_dir is not None:
        diagnostics_dir.mkdir(parents=True, exist_ok=True)
        diagnostics_path = diagnostics_dir / f"{Path(clip).stem}.json"
        audit["vehicle_speed_diagnostics_path"] = str(diagnostics_path)
    if audit_path is not None:
        audit_path.write_text(_json_dumps(audit), encoding="utf-8")
    if diagnostics_path is not None:
        diagnostics_path.write_text(_json_dumps(audit), encoding="utf-8")
    return audit


def _json_dumps(payload: dict[str, Any]) -> str:
    import json

    return json.dumps(payload, ensure_ascii=False, indent=2)


def _update_counter(counter: Counter[str], value: object) -> None:
    if not isinstance(value, dict):
        return
    for key, count in value.items():
        try:
            counter[str(key)] += int(count)
        except (TypeError, ValueError):
            continue


def _merge_max_speed(target: dict[str, float], value: object) -> None:
    if not isinstance(value, dict):
        return
    for key, speed in value.items():
        try:
            target[str(key)] = max(target.get(str(key), 0.0), float(speed))
        except (TypeError, ValueError):
            continue


def _max_vehicle_speed(audit: dict[str, Any]) -> float:
    return _max_speed_from_mapping(
        audit.get("max_speed_by_class") if isinstance(audit, dict) else {},
    )


def _max_speed_from_mapping(value: object) -> float:
    if not isinstance(value, dict) or not value:
        return 0.0
    speeds: list[float] = []
    for speed in value.values():
        try:
            speeds.append(float(speed))
        except (TypeError, ValueError):
            continue
    return max(speeds, default=0.0)


def _passes_quality_gate(audit: dict[str, Any]) -> bool:
    return (
        int(audit.get("hard_rejected_display_count") or 0) == 0
        and int(audit.get("displayed_id_switch_risk_count") or 0) == 0
        and float(audit.get("displayed_high_uncertainty_ratio") or 0.0)
        <= DISPLAYED_HIGH_UNCERTAINTY_MAX_RATIO
        and float(audit.get("displayed_low_confidence_ratio") or 0.0)
        <= DISPLAYED_LOW_CONFIDENCE_MAX_RATIO
        and int(audit.get("max_consecutive_frozen_frames") or 0)
        <= FROZEN_LAST_VALID_WINDOW_FRAMES
    )


def _coverage_for_gate(audit: dict[str, Any]) -> float | None:
    coverage = audit.get("vehicle_display_coverage")
    total_coverage = float(coverage) if isinstance(coverage, int | float) else None
    if (
        "safe_vehicle_track_samples" in audit
        or "safe_displayable_vehicle_track_samples" in audit
        or "safe_vehicle_display_coverage" in audit
    ):
        safe_samples = _int_or_default(audit.get("safe_vehicle_track_samples"), 0)
        if safe_samples <= 0:
            return None
        safe_coverage = audit.get("safe_vehicle_display_coverage")
        if isinstance(safe_coverage, int | float):
            return _combined_gate_coverage(
                total_coverage,
                float(safe_coverage),
                safe_schema_seen=True,
            )
        safe_displayable = _int_or_default(
            audit.get("safe_displayable_vehicle_track_samples"),
            0,
        )
        return _combined_gate_coverage(
            total_coverage,
            safe_displayable / safe_samples,
            safe_schema_seen=True,
        )
    if total_coverage is not None:
        return total_coverage
    return None


def _combined_gate_coverage(
    total_coverage: float | None,
    safe_coverage: float | None,
    *,
    safe_schema_seen: bool,
) -> float | None:
    if not safe_schema_seen:
        return total_coverage
    if total_coverage is None or safe_coverage is None:
        return None
    return min(total_coverage, safe_coverage)


def _is_vehicle(track: dict[str, Any]) -> bool:
    try:
        return int(track.get("class_id", -1)) in VEHICLE_CLASS_IDS
    except (TypeError, ValueError):
        return False


def _is_displayable(track: dict[str, Any]) -> bool:
    return track.get("speed_kmh") is not None and bool(track.get("physics_valid", False))


def _is_safe_vehicle_sample(track: dict[str, Any]) -> bool:
    if _is_hard_rejected(track) or _id_switch_risk(track) >= ID_SWITCH_DISPLAY_THRESHOLD:
        return False
    if track.get("speed_kmh") is None and _is_warming_up(track):
        return False
    speed = _optional_float(track.get("speed_kmh"))
    return speed is None or 0.0 <= speed <= CAR_HARD_MAX_KMH


def _should_hide_displayable_vehicle_speed(track: dict[str, Any]) -> bool:
    if track.get("speed_kmh") is None:
        return False
    if _is_hard_rejected(track) or _id_switch_risk(track) >= ID_SWITCH_DISPLAY_THRESHOLD:
        return True
    return bool(track.get("bbox_center_fallback")) and (
        _is_low_confidence(track) or _is_high_uncertainty(track)
    )


def _annotate_contact_quality(track: dict[str, Any]) -> None:
    source = _contact_point_source(track)
    track["contact_point_source"] = source
    track["bbox_center_fallback"] = _is_bbox_center_source(source)
    uncertainty_px = _contact_uncertainty_px(track)
    uncertainty_m = _contact_uncertainty_m(track, uncertainty_px)
    if uncertainty_px is not None:
        track["contact_point_uncertainty_px"] = uncertainty_px
    if uncertainty_m is not None:
        track["contact_point_uncertainty_m"] = uncertainty_m
    quality = _contact_quality_score(track, uncertainty_px, uncertainty_m)
    track["contact_point_quality_score"] = quality
    track["contact_point_dominant_error_source"] = _contact_dominant_error_source(
        track,
        uncertainty_px,
        uncertainty_m,
    )
    if track["bbox_center_fallback"]:
        track["speed_validity_score"] = min(
            float(track.get("speed_validity_score") or quality),
            max(0.0, quality - 0.2),
        )
        current_confidence = _optional_float(track.get("speed_confidence"))
        track["speed_confidence"] = min(
            current_confidence
            if current_confidence is not None
            else BBOX_CENTER_FALLBACK_MAX_CONFIDENCE,
            BBOX_CENTER_FALLBACK_MAX_CONFIDENCE,
        )
        if track.get("speed_uncertainty_kmh") is not None:
            track["speed_uncertainty_kmh"] = max(
                float(track["speed_uncertainty_kmh"]),
                BBOX_CENTER_FALLBACK_MIN_UNCERTAINTY_KMH,
            )
        elif track.get("speed_kmh") is not None:
            track["speed_uncertainty_kmh"] = BBOX_CENTER_FALLBACK_MIN_UNCERTAINTY_KMH


def _contact_point_source(track: dict[str, Any]) -> str:
    for key in ("contact_source", "measurement_source"):
        value = track.get(key)
        if value:
            return str(value)
    sources = track.get("contact_fusion_sources")
    if isinstance(sources, list) and sources:
        return "+".join(str(source) for source in sources)
    return "unknown"


def _is_bbox_center_source(source: str) -> bool:
    normalized = source.lower()
    return "bbox_center" in normalized or normalized == "center"


def _contact_uncertainty_px(track: dict[str, Any]) -> float | None:
    covariance = track.get("contact_pixel_covariance")
    if (
        isinstance(covariance, list)
        and len(covariance) >= 2
        and isinstance(covariance[0], list)
        and isinstance(covariance[1], list)
        and len(covariance[0]) >= 1
        and len(covariance[1]) >= 2
    ):
        xx = _optional_float(covariance[0][0])
        yy = _optional_float(covariance[1][1])
        if xx is not None and yy is not None:
            variance = max(0.0, (xx + yy) / 2.0)
            return float(variance**0.5)
    for key in ("point_homography_std_px", "observation_sigma_px"):
        value = _optional_float(track.get(key))
        if value is not None:
            return value
    return None


def _contact_uncertainty_m(
    track: dict[str, Any],
    uncertainty_px: float | None,
) -> float | None:
    position_sigma = _optional_float(track.get("position_sigma_m"))
    if position_sigma is not None:
        return position_sigma
    local_scale = _optional_float(track.get("local_scale_factor"))
    if uncertainty_px is not None and local_scale is not None:
        return float(max(0.0, uncertainty_px * local_scale))
    return _optional_float(track.get("point_homography_std_m"))


def _contact_quality_score(
    track: dict[str, Any],
    uncertainty_px: float | None,
    uncertainty_m: float | None,
) -> float:
    candidates = [
        _optional_float(track.get("contact_quality_score")),
        _optional_float(track.get("contact_fusion_confidence")),
        _optional_float(track.get("contact_confidence")),
        _optional_float(track.get("measurement_confidence")),
        _optional_float(track.get("optical_flow_inlier_ratio")),
    ]
    values = [value for value in candidates if value is not None]
    score = mean(values) if values else 0.55
    if track.get("bbox_center_fallback"):
        score -= 0.25
    if uncertainty_px is not None:
        score -= min(0.25, uncertainty_px / 80.0)
    if uncertainty_m is not None:
        score -= min(0.25, uncertainty_m / 8.0)
    if track.get("contact_outlier_source"):
        score -= 0.2
    if track.get("measurement_policy") in {"reject", "predict_only"}:
        score -= 0.25
    return float(max(0.0, min(1.0, score)))


def _contact_dominant_error_source(
    track: dict[str, Any],
    uncertainty_px: float | None,
    uncertainty_m: float | None,
) -> str:
    if track.get("bbox_center_fallback"):
        return "bbox_center_fallback"
    if track.get("contact_outlier_source"):
        return str(track["contact_outlier_source"])
    if uncertainty_m is not None and uncertainty_m > 2.0:
        return "metric_contact_uncertainty"
    if uncertainty_px is not None and uncertainty_px > 12.0:
        return "pixel_contact_uncertainty"
    if track.get("dominant_uncertainty_source"):
        return str(track["dominant_uncertainty_source"])
    return "none"


def _is_low_confidence(track: dict[str, Any]) -> bool:
    confidence = _optional_float(track.get("speed_confidence"))
    if confidence is None:
        return False
    return confidence < LOW_CONFIDENCE_THRESHOLD


def _is_high_uncertainty(track: dict[str, Any]) -> bool:
    uncertainty = _optional_float(track.get("speed_uncertainty_kmh"))
    if uncertainty is not None and uncertainty > HIGH_UNCERTAINTY_KMH:
        return True
    interval = track.get("speed_confidence_interval_kmh")
    if isinstance(interval, list) and len(interval) == 2:
        lower = _optional_float(interval[0])
        upper = _optional_float(interval[1])
        if lower is not None and upper is not None:
            return upper - lower > HIGH_INTERVAL_WIDTH_KMH
    return False


def _is_warming_up(track: dict[str, Any]) -> bool:
    quality = str(track.get("quality_label") or "")
    stability = str(track.get("stability_label") or "")
    try:
        age = int(track.get("track_age_frames") or 0)
    except (TypeError, ValueError):
        age = 0
    return quality == "warming_up" or stability == "insufficient_samples" or age <= 2


def _can_freeze(
    track: dict[str, Any],
    previous: dict[str, Any] | None,
    frame_index: int,
    freeze_window_frames: int,
) -> bool:
    if previous is None:
        return False
    if frame_index - int(previous["frame_index"]) > freeze_window_frames:
        return False
    if _is_hard_rejected(track) or _id_switch_risk(track) >= 0.7:
        return False
    return not _is_warming_up(track)


def _backfill_vehicle_warmup_speeds(
    frame_reports: list[dict[str, Any]],
    max_gap_frames: int,
) -> None:
    next_valid: dict[tuple[int, int], dict[str, Any]] = {}
    for fallback_index, report in reversed(list(enumerate(frame_reports))):
        frame_index = _frame_index(report, fallback_index)
        for track in report.get("active_tracks", []):
            if not isinstance(track, dict) or not _is_vehicle(track):
                continue
            key = (int(track.get("tracker_id", -1)), int(track.get("class_id", -1)))
            if _is_displayable(track):
                next_valid[key] = {
                    "frame_index": frame_index,
                    "speed_kmh": float(track["speed_kmh"]),
                    "speed_uncertainty_kmh": track.get("speed_uncertainty_kmh"),
                    "speed_confidence": track.get("speed_confidence"),
                    "speed_confidence_interval_kmh": track.get(
                        "speed_confidence_interval_kmh",
                    ),
                }
                continue
            future = next_valid.get(key)
            if not _can_backfill_warmup(track, future, frame_index, max_gap_frames):
                continue
            track["speed_kmh"] = future["speed_kmh"]
            track["speed_uncertainty_kmh"] = future.get("speed_uncertainty_kmh")
            track["speed_confidence"] = future.get("speed_confidence")
            track["speed_confidence_interval_kmh"] = future.get(
                "speed_confidence_interval_kmh",
            )
            track["physics_valid"] = True
            track["speed_source"] = "fixed_lag_warmup_backfill"
            track["fixed_lag_backfilled"] = True
            track["vehicle_speed_display_state"] = "fixed_lag_refined"
            track["vehicle_speed_warmup_backfilled"] = True
            track["speed_display_hidden"] = False


def _recalibrate_stable_fixed_lag_rts_speeds(
    frame_reports: list[dict[str, Any]],
) -> None:
    samples_by_track: defaultdict[tuple[int, int], list[dict[str, Any]]] = defaultdict(
        list,
    )
    for fallback_index, report in enumerate(frame_reports):
        frame_index = _frame_index(report, fallback_index)
        timestamp = _timestamp_sec(report, frame_index)
        for track in report.get("active_tracks", []):
            if not isinstance(track, dict) or not _is_rts_recalibration_candidate(track):
                continue
            speed = _optional_float(track.get("speed_kmh"))
            if speed is None:
                continue
            key = (int(track.get("tracker_id", -1)), int(track.get("class_id", -1)))
            samples_by_track[key].append(
                {
                    "frame_index": frame_index,
                    "timestamp": timestamp,
                    "speed": speed,
                    "track": track,
                    "contact_quality": _optional_float(
                        track.get("contact_point_quality_score"),
                    )
                    or 0.0,
                },
            )

    for samples in samples_by_track.values():
        ordered = sorted(samples, key=lambda sample: int(sample["frame_index"]))
        stats = _fixed_lag_stability_stats(ordered)
        if not _has_stable_fixed_lag_rts_profile(ordered, stats):
            continue
        target_uncertainty = _calibrated_rts_uncertainty_kmh(stats)
        target_confidence = _calibrated_rts_confidence(stats)
        for sample in ordered:
            track = sample["track"]
            if not isinstance(track, dict):
                continue
            current_uncertainty = _optional_float(track.get("speed_uncertainty_kmh"))
            uncertainty = (
                target_uncertainty
                if current_uncertainty is None
                else min(current_uncertainty, target_uncertainty)
            )
            current_confidence = _optional_float(track.get("speed_confidence"))
            confidence = max(current_confidence or 0.0, target_confidence)
            speed = float(sample["speed"])
            half_width = min(
                HIGH_INTERVAL_WIDTH_KMH / 2.0 - 0.1,
                max(3.0, uncertainty * RTS_RECALIBRATION_INTERVAL_SIGMA),
            )
            track["speed_uncertainty_kmh"] = round(uncertainty, 6)
            track["speed_confidence"] = round(min(1.0, confidence), 6)
            track["speed_confidence_interval_kmh"] = [
                round(max(0.0, speed - half_width), 6),
                round(speed + half_width, 6),
            ]
            track["physics_valid"] = True
            track["speed_source"] = "fixed_lag_rts_calibrated"
            track["fixed_lag_backfilled"] = True
            track["speed_uncertainty_recalibrated"] = True
            track["vehicle_speed_recovered_from_stable_rts"] = True
            track["vehicle_speed_display_state"] = "fixed_lag_refined"
            track["speed_display_hidden"] = False
            track["rts_recalibration_profile"] = {
                "sample_count": int(stats["sample_count"]),
                "speed_jump_p95_kmh": round(float(stats["speed_jump_p95_kmh"]), 6),
                "acceleration_p95_mps2": round(float(stats["acceleration_p95_mps2"]), 6),
                "jerk_p95_mps3": round(float(stats["jerk_p95_mps3"]), 6),
                "median_contact_quality": round(
                    float(stats["median_contact_quality"]),
                    6,
                ),
            }


def _is_rts_recalibration_candidate(track: dict[str, Any]) -> bool:
    source = str(track.get("speed_source") or "")
    if not source.startswith("fixed_lag_rts"):
        return False
    if bool(track.get("speed_uncertainty_recalibrated")):
        return False
    if bool(track.get("bbox_center_fallback")):
        return False
    if track.get("speed_kmh") is None:
        return False
    if _is_hard_rejected(track) or _id_switch_risk(track) >= ID_SWITCH_DISPLAY_THRESHOLD:
        return False
    speed = _optional_float(track.get("speed_kmh"))
    return speed is not None and 0.0 <= speed <= CAR_HARD_MAX_KMH


def _fixed_lag_stability_stats(samples: list[dict[str, Any]]) -> dict[str, float]:
    speeds = [float(sample["speed"]) for sample in samples]
    jumps: list[float] = []
    accelerations: list[float] = []
    jerks: list[float] = []
    for previous, current in zip(samples, samples[1:], strict=False):
        jumps.append(abs(float(current["speed"]) - float(previous["speed"])))
    for left, middle, right in zip(samples, samples[1:], samples[2:], strict=False):
        dt_left = max(float(middle["timestamp"]) - float(left["timestamp"]), 1e-6)
        dt_right = max(float(right["timestamp"]) - float(middle["timestamp"]), 1e-6)
        accel_left = ((float(middle["speed"]) - float(left["speed"])) / 3.6) / dt_left
        accel_right = ((float(right["speed"]) - float(middle["speed"])) / 3.6) / dt_right
        accelerations.extend([abs(accel_left), abs(accel_right)])
        jerks.append(abs(accel_right - accel_left) / max(dt_right, 1e-6))
    contact_quality_values = [
        float(sample["contact_quality"])
        for sample in samples
        if _optional_float(sample.get("contact_quality")) is not None
    ]
    return {
        "sample_count": float(len(samples)),
        "speed_std_kmh": float(pstdev(speeds)) if len(speeds) > 1 else 0.0,
        "speed_jump_p95_kmh": _p95(jumps) or 0.0,
        "acceleration_p95_mps2": _p95(accelerations) or 0.0,
        "jerk_p95_mps3": _p95(jerks) or 0.0,
        "median_contact_quality": (
            float(median(contact_quality_values)) if contact_quality_values else 0.0
        ),
    }


def _has_stable_fixed_lag_rts_profile(
    samples: list[dict[str, Any]],
    stats: dict[str, float],
) -> bool:
    return (
        len(samples) >= RTS_RECALIBRATION_MIN_TRACK_SAMPLES
        and stats["speed_jump_p95_kmh"] <= RTS_RECALIBRATION_MAX_SPEED_JUMP_KMH
        and stats["acceleration_p95_mps2"] <= RTS_RECALIBRATION_MAX_ACCEL_MPS2
        and stats["jerk_p95_mps3"] <= RTS_RECALIBRATION_MAX_JERK_MPS3
        and stats["median_contact_quality"] >= RTS_RECALIBRATION_MIN_CONTACT_QUALITY
    )


def _calibrated_rts_uncertainty_kmh(stats: dict[str, float]) -> float:
    variability = max(
        2.0,
        stats["speed_std_kmh"] * 1.5,
        stats["speed_jump_p95_kmh"] * 2.0,
        stats["acceleration_p95_mps2"] * 0.8,
    )
    return float(min(RTS_RECALIBRATION_MAX_UNCERTAINTY_KMH, variability))


def _calibrated_rts_confidence(stats: dict[str, float]) -> float:
    smoothness_penalty = min(0.25, stats["speed_jump_p95_kmh"] / 40.0)
    dynamics_penalty = min(0.2, stats["acceleration_p95_mps2"] / 25.0)
    contact_bonus = min(0.25, stats["median_contact_quality"] * 0.25)
    return max(
        RTS_RECALIBRATION_MIN_CONFIDENCE,
        min(0.85, 0.45 + contact_bonus - smoothness_penalty - dynamics_penalty),
    )


def _downgrade_stable_world_jump_id_switch_risks(
    frame_reports: list[dict[str, Any]],
) -> None:
    samples_by_track: defaultdict[tuple[int, int], list[dict[str, Any]]] = defaultdict(
        list,
    )
    for fallback_index, report in enumerate(frame_reports):
        frame_index = _frame_index(report, fallback_index)
        timestamp = _timestamp_sec(report, frame_index)
        for track in report.get("active_tracks", []):
            if not isinstance(track, dict) or not _is_vehicle(track):
                continue
            speed = _optional_float(track.get("speed_kmh"))
            if speed is None:
                continue
            source = str(track.get("speed_source") or "")
            if not source.startswith("fixed_lag_rts"):
                continue
            key = (int(track.get("tracker_id", -1)), int(track.get("class_id", -1)))
            samples_by_track[key].append(
                {
                    "frame_index": frame_index,
                    "timestamp": timestamp,
                    "speed": speed,
                    "track": track,
                    "contact_quality": _optional_float(
                        track.get("contact_point_quality_score"),
                    )
                    or 0.0,
                },
            )

    for samples in samples_by_track.values():
        ordered = sorted(samples, key=lambda sample: int(sample["frame_index"]))
        stats = _fixed_lag_stability_stats(ordered)
        if not _has_stable_fixed_lag_rts_profile(ordered, stats):
            continue
        for sample in ordered:
            track = sample["track"]
            if not isinstance(track, dict):
                continue
            if not _is_stable_world_jump_id_switch_candidate(track):
                continue
            original_risk = _id_switch_risk(track)
            uncertainty = max(
                _optional_float(track.get("speed_uncertainty_kmh")) or 0.0,
                ID_SWITCH_POSTERIOR_MIN_UNCERTAINTY_KMH,
            )
            confidence = max(
                _optional_float(track.get("speed_confidence")) or 0.0,
                ID_SWITCH_POSTERIOR_MIN_CONFIDENCE,
            )
            speed = float(sample["speed"])
            half_width = max(3.0, uncertainty * RTS_RECALIBRATION_INTERVAL_SIGMA)
            track["id_switch_risk_original"] = original_risk
            track["id_switch_risk"] = ID_SWITCH_POSTERIOR_RISK
            track["id_switch_risk_posterior"] = ID_SWITCH_POSTERIOR_RISK
            track["id_switch_risk_downgraded"] = True
            track["id_switch_risk_downgrade_reason"] = (
                "stable_rts_world_jump_posterior"
            )
            track["id_switch_risk_review_profile"] = {
                "sample_count": int(stats["sample_count"]),
                "speed_jump_p95_kmh": round(float(stats["speed_jump_p95_kmh"]), 6),
                "acceleration_p95_mps2": round(float(stats["acceleration_p95_mps2"]), 6),
                "jerk_p95_mps3": round(float(stats["jerk_p95_mps3"]), 6),
                "median_contact_quality": round(
                    float(stats["median_contact_quality"]),
                    6,
                ),
            }
            track["physics_valid"] = True
            track["speed_display_hidden"] = False
            track["vehicle_speed_display_state"] = "fixed_lag_refined"
            track["speed_uncertainty_kmh"] = round(uncertainty, 6)
            track["speed_confidence"] = round(min(1.0, confidence), 6)
            track["speed_confidence_interval_kmh"] = [
                round(max(0.0, speed - half_width), 6),
                round(speed + half_width, 6),
            ]
            track["speed_source"] = "fixed_lag_rts_idrisk_reviewed"


def _is_stable_world_jump_id_switch_candidate(track: dict[str, Any]) -> bool:
    if _is_hard_rejected(track):
        return False
    if _id_switch_risk(track) < ID_SWITCH_DISPLAY_THRESHOLD:
        return False
    if str(track.get("integrity_rejection_reason") or "") != "world_position_jump":
        return False
    if str(track.get("tracking_integrity_state") or "") != "suspected_id_switch":
        return False
    if str(track.get("bev_risk_level") or "") != "trusted":
        return False
    if bool(track.get("bbox_center_fallback")):
        return False
    if str(track.get("quality_label") or "") != "stable":
        return False
    if str(track.get("stability_label") or "") != "stable":
        return False
    source = str(track.get("speed_source") or "")
    if not source.startswith("fixed_lag_rts"):
        return False
    speed = _optional_float(track.get("speed_kmh"))
    if speed is None or speed < 0.0 or speed > CAR_HARD_MAX_KMH:
        return False
    uncertainty = _optional_float(track.get("speed_uncertainty_kmh"))
    if uncertainty is not None and uncertainty > RTS_RECALIBRATION_MAX_UNCERTAINTY_KMH:
        return False
    confidence = _optional_float(track.get("speed_confidence"))
    if confidence is not None and confidence < RECONSTRUCTED_SPEED_MIN_CONFIDENCE:
        return False
    return True


def _can_backfill_warmup(
    track: dict[str, Any],
    future: dict[str, Any] | None,
    frame_index: int,
    max_gap_frames: int,
) -> bool:
    if future is None:
        return False
    if int(future["frame_index"]) - frame_index > max_gap_frames:
        return False
    if not _is_warming_up(track):
        return False
    if _is_hard_rejected(track) or _id_switch_risk(track) >= 0.7:
        return False
    return track.get("speed_kmh") is None


def _can_admit_reconstructed_vehicle_speed(track: dict[str, Any]) -> bool:
    if track.get("speed_kmh") is None:
        return False
    if not _is_fixed_lag_reconstructed(track):
        return False
    if _is_hard_rejected(track) or _id_switch_risk(track) >= 0.7:
        return False
    try:
        speed = float(track["speed_kmh"])
    except (TypeError, ValueError):
        return False
    if speed < 0.0 or speed > CAR_HARD_MAX_KMH:
        return False
    return _has_usable_reconstructed_speed_quality(track)


def _is_fixed_lag_reconstructed(track: dict[str, Any]) -> bool:
    return bool(track.get("fixed_lag_backfilled")) or str(
        track.get("speed_source") or "",
    ).startswith("fixed_lag")


def _has_usable_reconstructed_speed_quality(track: dict[str, Any]) -> bool:
    uncertainty = _optional_float(track.get("speed_uncertainty_kmh"))
    confidence = _optional_float(track.get("speed_confidence"))
    if uncertainty is None and confidence is None:
        return True
    if uncertainty is not None and uncertainty <= RECONSTRUCTED_SPEED_MAX_UNCERTAINTY_KMH:
        return True
    return confidence is not None and confidence >= RECONSTRUCTED_SPEED_MIN_CONFIDENCE


def _is_hard_rejected(track: dict[str, Any]) -> bool:
    quality = str(track.get("quality_label") or "")
    reasons = {
        str(track.get("rejection_reason") or ""),
        str(track.get("confidence_rejection_reason") or ""),
        str(track.get("integrity_rejection_reason") or ""),
        str(track.get("association_rejection_reason") or ""),
    }
    return quality == "rejected" or bool(HARD_REJECTION_REASONS.intersection(reasons))


def _id_switch_risk(track: dict[str, Any]) -> float:
    try:
        return float(track.get("id_switch_risk") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int_or_default(value: object, default: int) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def build_vehicle_3d_scale_sanity(frame_reports: list[dict[str, Any]]) -> dict[str, Any]:
    displayable_tracks: list[dict[str, Any]] = []
    calibration_3d = None
    for report in frame_reports:
        diagnostics = report.get("calibration_diagnostics")
        if isinstance(diagnostics, dict) and calibration_3d is None:
            calibration_3d = diagnostics.get("calibration_3d_diagnostics")
        for track in report.get("active_tracks", []):
            if isinstance(track, dict) and _is_vehicle(track) and _is_displayable(track):
                displayable_tracks.append(track)
    if not displayable_tracks:
        return {
            "available": False,
            "reason": "no_displayable_vehicle_tracks",
            "model_reference": "vehicle_3d_scale_sanity_v1",
        }
    global_speed = median(
        [
            float(track["speed_kmh"])
            for track in displayable_tracks
            if track.get("speed_kmh") is not None
        ],
    )
    y_bins = _speed_bias_by_bucket(displayable_tracks, "ground_y_m", global_speed)
    lane_bins = _speed_bias_by_bucket(displayable_tracks, "plane_id", global_speed)
    bbox_errors = _bbox_size_consistency_errors(displayable_tracks)
    mean_bbox_error = mean(bbox_errors) if bbox_errors else None
    max_abs_y_bias = max(
        (abs(float(row["speed_bias_kmh"])) for row in y_bins.values()),
        default=0.0,
    )
    multiplier = 1.0
    if mean_bbox_error is not None:
        multiplier += min(1.5, mean_bbox_error)
    multiplier += min(1.0, max_abs_y_bias / 20.0)
    quality = "good"
    if multiplier > 2.0:
        quality = "review"
    if multiplier > 3.0:
        quality = "poor"
    return {
        "available": True,
        "calibration_3d_available": bool(calibration_3d),
        "calibration_3d_diagnostics": calibration_3d if isinstance(calibration_3d, dict) else {},
        "scale_bias_by_y_depth": y_bins,
        "scale_bias_by_lane_zone": lane_bins,
        "bbox_size_consistency_error": mean_bbox_error,
        "homography_uncertainty_multiplier": round(multiplier, 6),
        "calibration_region_quality": quality,
        "model_reference": "vehicle_3d_prior_scale_sanity_v1",
    }


def _speed_bias_by_bucket(
    tracks: list[dict[str, Any]],
    field: str,
    global_speed: float,
) -> dict[str, dict[str, float | int]]:
    buckets: defaultdict[str, list[float]] = defaultdict(list)
    if field == "ground_y_m":
        values = [
            _optional_float(track.get("ground_y_m"))
            for track in tracks
            if track.get("ground_y_m") is not None
        ]
        valid_values = sorted(value for value in values if value is not None)
        if not valid_values:
            return {}
        first_cut = valid_values[int((len(valid_values) - 1) * 0.33)]
        second_cut = valid_values[int((len(valid_values) - 1) * 0.66)]
        for track in tracks:
            y = _optional_float(track.get("ground_y_m"))
            speed = _optional_float(track.get("speed_kmh"))
            if y is None or speed is None:
                continue
            bucket = "near" if y <= first_cut else "mid" if y <= second_cut else "far"
            buckets[bucket].append(speed)
    else:
        for track in tracks:
            speed = _optional_float(track.get("speed_kmh"))
            if speed is None:
                continue
            buckets[str(track.get(field) or "unknown")].append(speed)
    return {
        name: {
            "sample_count": len(values),
            "median_speed_kmh": float(median(values)),
            "speed_bias_kmh": float(median(values) - global_speed),
        }
        for name, values in sorted(buckets.items())
        if values
    }


def _bbox_size_consistency_errors(tracks: list[dict[str, Any]]) -> list[float]:
    errors: list[float] = []
    for track in tracks:
        xyxy = track.get("xyxy")
        local_scale = _optional_float(track.get("local_scale_factor"))
        class_name = str(track.get("class_name") or "").lower()
        expected_width = VEHICLE_WIDTH_PRIOR_M.get(class_name)
        if (
            not isinstance(xyxy, list)
            or len(xyxy) < 4
            or local_scale is None
            or expected_width is None
            or expected_width <= 0
        ):
            continue
        left = _optional_float(xyxy[0])
        right = _optional_float(xyxy[2])
        if left is None or right is None:
            continue
        estimated_width = abs(right - left) * local_scale
        errors.append(abs(estimated_width - expected_width) / expected_width)
    return errors


def build_speed_ground_truth_metrics(
    frame_reports: list[dict[str, Any]],
    *,
    clip: str | None,
    speed_ground_truth_dir: Path | None,
) -> dict[str, Any]:
    rows = _load_ground_truth_rows(clip, speed_ground_truth_dir)
    if not rows:
        return {
            "available": False,
            "proxy_only": True,
            "model_reference": "optional_speed_ground_truth_metrics_v1",
        }
    track_samples = _displayable_tracks_by_id(frame_reports)
    errors: list[float] = []
    signed_errors: list[float] = []
    predicted_speeds: list[float] = []
    gt_speeds: list[float] = []
    predicted_uncertainties: list[float] = []
    predicted_confidences: list[float] = []
    p50_hits = 0
    p90_hits = 0
    interval_widths: list[float] = []
    matched = 0
    for row in rows:
        key = (int(row["tracker_id"]), str(row["class_name"]).lower())
        samples = track_samples.get(key, [])
        selected = [
            sample
            for sample in samples
            if int(row["frame_start"])
            <= int(sample["frame_index"])
            <= int(row["frame_end"])
        ]
        if not selected:
            continue
        predicted = mean(float(sample["speed_kmh"]) for sample in selected)
        gt_speed = float(row["gt_speed_kmh"])
        error = predicted - gt_speed
        predicted_speeds.append(predicted)
        gt_speeds.append(gt_speed)
        signed_errors.append(error)
        errors.append(abs(error))
        matched += 1
        uncertainties = [
            float(sample["speed_uncertainty_kmh"])
            for sample in selected
            if _optional_float(sample.get("speed_uncertainty_kmh")) is not None
        ]
        if uncertainties:
            predicted_uncertainties.append(mean(uncertainties))
        confidences = [
            float(sample["speed_confidence"])
            for sample in selected
            if _optional_float(sample.get("speed_confidence")) is not None
        ]
        if confidences:
            predicted_confidences.append(mean(confidences))
        intervals = [
            sample.get("speed_confidence_interval_kmh")
            for sample in selected
            if isinstance(sample.get("speed_confidence_interval_kmh"), list)
            and len(sample["speed_confidence_interval_kmh"]) == 2
        ]
        if intervals:
            lower = median(float(interval[0]) for interval in intervals)
            upper = median(float(interval[1]) for interval in intervals)
            interval_widths.append(max(0.0, upper - lower))
            p50_half_width = (upper - lower) * 0.25
            center = (upper + lower) / 2.0
            p50_hits += int(
                center - p50_half_width <= gt_speed <= center + p50_half_width,
            )
            p90_hits += int(lower <= gt_speed <= upper)
    if not errors:
        return {
            "available": True,
            "matched_count": 0,
            "unmatched_count": len(rows),
            "proxy_only": False,
            "model_reference": "optional_speed_ground_truth_metrics_v1",
        }
    rmse = float((mean([error**2 for error in signed_errors])) ** 0.5)
    signed_bias = float(mean(signed_errors))
    p90_coverage = p90_hits / matched if matched else None
    mean_uncertainty = mean(predicted_uncertainties) if predicted_uncertainties else None
    uncertainty_ratio = (
        rmse / max(mean_uncertainty, 1e-6)
        if mean_uncertainty is not None
        else None
    )
    suggested_multiplier = _suggested_gt_uncertainty_multiplier(
        rmse=rmse,
        mean_uncertainty=mean_uncertainty,
        p90_coverage=p90_coverage,
    )
    return {
        "available": True,
        "matched_count": matched,
        "unmatched_count": max(0, len(rows) - matched),
        "speed_mae_kmh": float(mean(errors)),
        "speed_rmse_kmh": rmse,
        "speed_median_ae_kmh": float(median(errors)),
        "speed_p95_ae_kmh": _p95(errors),
        "signed_bias_kmh": signed_bias,
        "bias_correction_kmh": -signed_bias,
        "mean_predicted_speed_kmh": float(mean(predicted_speeds)),
        "mean_gt_speed_kmh": float(mean(gt_speeds)),
        "mean_predicted_uncertainty_kmh": mean_uncertainty,
        "mean_predicted_confidence": (
            mean(predicted_confidences) if predicted_confidences else None
        ),
        "uncertainty_calibration_ratio": uncertainty_ratio,
        "suggested_uncertainty_multiplier": suggested_multiplier,
        "calibration_status": _gt_calibration_status(
            signed_bias=signed_bias,
            rmse=rmse,
            p90_coverage=p90_coverage,
            uncertainty_ratio=uncertainty_ratio,
        ),
        "within_3_kmh_ratio": _within_ratio(errors, 3.0),
        "within_5_kmh_ratio": _within_ratio(errors, 5.0),
        "within_10_kmh_ratio": _within_ratio(errors, 10.0),
        "p50_interval_coverage": p50_hits / matched if matched else None,
        "p90_interval_coverage": p90_coverage,
        "mean_interval_width_kmh": mean(interval_widths) if interval_widths else None,
        "proxy_only": False,
        "model_reference": "optional_speed_ground_truth_metrics_v1",
    }


def _suggested_gt_uncertainty_multiplier(
    *,
    rmse: float,
    mean_uncertainty: float | None,
    p90_coverage: float | None,
) -> float | None:
    if mean_uncertainty is None or mean_uncertainty <= 0.0:
        return None
    multiplier = max(0.5, min(4.0, rmse / max(mean_uncertainty, 1e-6)))
    if p90_coverage is not None and p90_coverage < 0.8:
        multiplier = max(multiplier, 1.25)
    if p90_coverage is not None and p90_coverage >= 0.98 and multiplier < 1.0:
        multiplier = max(0.5, multiplier)
    return float(round(multiplier, 6))


def _gt_calibration_status(
    *,
    signed_bias: float,
    rmse: float,
    p90_coverage: float | None,
    uncertainty_ratio: float | None,
) -> str:
    if abs(signed_bias) >= 5.0:
        return "biased_speed"
    if p90_coverage is not None and p90_coverage < 0.8:
        return "undercovered_intervals"
    if uncertainty_ratio is not None and uncertainty_ratio > 1.5:
        return "underestimated_uncertainty"
    if uncertainty_ratio is not None and uncertainty_ratio < 0.35 and rmse < 3.0:
        return "overconservative_uncertainty"
    return "calibrated"


def _load_ground_truth_rows(
    clip: str | None,
    speed_ground_truth_dir: Path | None,
) -> list[dict[str, Any]]:
    if (
        clip is None
        or speed_ground_truth_dir is None
        or not speed_ground_truth_dir.exists()
    ):
        return []
    rows: list[dict[str, Any]] = []
    candidates = [
        speed_ground_truth_dir / f"{Path(clip).stem}.csv",
        speed_ground_truth_dir / "speed_ground_truth.csv",
    ]
    for path in candidates:
        if not path.exists():
            continue
        with path.open(newline="", encoding="utf-8") as handle:
            for row in DictReader(handle):
                if row.get("clip") not in {None, "", clip}:
                    continue
                try:
                    rows.append(
                        {
                            "clip": row.get("clip") or clip,
                            "tracker_id": int(row["tracker_id"]),
                            "frame_start": int(row["frame_start"]),
                            "frame_end": int(row["frame_end"]),
                            "class_name": str(row["class_name"]),
                            "gt_speed_kmh": float(row["gt_speed_kmh"]),
                            "source": row.get("source"),
                            "confidence": float(row.get("confidence") or 1.0),
                        },
                    )
                except (KeyError, TypeError, ValueError):
                    continue
    return rows


def _displayable_tracks_by_id(
    frame_reports: list[dict[str, Any]],
) -> dict[tuple[int, str], list[dict[str, Any]]]:
    tracks: defaultdict[tuple[int, str], list[dict[str, Any]]] = defaultdict(list)
    for fallback_index, report in enumerate(frame_reports):
        frame_index = _frame_index(report, fallback_index)
        for track in report.get("active_tracks", []):
            if (
                not isinstance(track, dict)
                or not _is_vehicle(track)
                or not _is_displayable(track)
            ):
                continue
            sample = dict(track)
            sample["frame_index"] = frame_index
            tracks[
                (
                    int(track.get("tracker_id", -1)),
                    str(track.get("class_name") or track.get("class_id")).lower(),
                )
            ].append(sample)
    return dict(tracks)


def _within_ratio(errors: list[float], threshold: float) -> float:
    if not errors:
        return 0.0
    return sum(1 for error in errors if error <= threshold) / len(errors)


def _invalid_reason(track: dict[str, Any]) -> str:
    for key in (
        "vehicle_speed_display_state",
        "rejection_reason",
        "confidence_rejection_reason",
        "integrity_rejection_reason",
        "association_rejection_reason",
        "quality_label",
        "stability_label",
    ):
        value = track.get(key)
        if value:
            return str(value)
    if track.get("speed_kmh") is None:
        return "speed_missing"
    return "physics_invalid"


def _frame_index(report: dict[str, Any], fallback_index: int) -> int:
    try:
        return int(report.get("frame_index", fallback_index))
    except (TypeError, ValueError):
        return fallback_index


def _timestamp_sec(report: dict[str, Any], frame_index: int) -> float:
    timestamp = _optional_float(report.get("timestamp_sec"))
    if timestamp is not None:
        return timestamp
    return frame_index / 30.0


def _append_float(values: list[float], value: object) -> None:
    if value is None:
        return
    try:
        values.append(float(value))
    except (TypeError, ValueError):
        return


def _append_abs_float(values: list[float], value: object) -> None:
    numeric = _optional_float(value)
    if numeric is not None:
        values.append(abs(numeric))


def _p95(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = int(round((len(ordered) - 1) * 0.95))
    return float(ordered[index] if len(ordered) > 2 else max(ordered, default=median(ordered)))
