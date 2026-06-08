from __future__ import annotations

import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median
from typing import Any

VEHICLE_CLASS_IDS = {2, 3, 5, 7}
VEHICLE_SPEED_REPORT_SCHEMA_VERSION = "vehicle_speed_report_v2"
FROZEN_LAST_VALID_WINDOW_FRAMES = 15
RECONSTRUCTED_SPEED_MAX_UNCERTAINTY_KMH = 30.0
RECONSTRUCTED_SPEED_MIN_CONFIDENCE = 0.05
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
            key = (int(track.get("tracker_id", -1)), int(track.get("class_id", -1)))
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
    return frame_reports


def build_vehicle_speed_audit(
    frame_reports: list[dict[str, Any]],
    *,
    clip: str | None = None,
    processed_video_path: str | None = None,
    source_commit_value: str | None = None,
) -> dict[str, Any]:
    counts: Counter[str] = Counter()
    na_by_reason: Counter[str] = Counter()
    physics_invalid_by_reason: Counter[str] = Counter()
    display_state_counts: Counter[str] = Counter()
    max_speed_by_class: dict[str, float] = {}
    speed_jump_values: list[float] = []
    speeds_by_track: defaultdict[tuple[int, int], list[float]] = defaultdict(list)

    for report in frame_reports:
        for track in report.get("active_tracks", []):
            if not isinstance(track, dict) or not _is_vehicle(track):
                continue
            counts["vehicle_track_samples"] += 1
            display_state = str(track.get("vehicle_speed_display_state") or "unknown")
            display_state_counts[display_state] += 1
            if bool(track.get("fixed_lag_backfilled")) or str(
                track.get("speed_source") or "",
            ).startswith("fixed_lag"):
                counts["fixed_lag_backfill_count"] += 1
            if (
                track.get("speed_source") == "frozen_last_valid"
                or track.get("vehicle_speed_display_state") == "frozen_last_valid"
            ):
                counts["frozen_last_valid_count"] += 1

            if _is_displayable(track):
                counts["displayable_vehicle_track_samples"] += 1
                speed = float(track["speed_kmh"])
                class_key = str(track.get("class_name") or track.get("class_id"))
                max_speed_by_class[class_key] = max(max_speed_by_class.get(class_key, 0.0), speed)
                speeds_by_track[
                    (int(track.get("tracker_id", -1)), int(track.get("class_id", -1)))
                ].append(speed)
                _append_float(speed_jump_values, track.get("speed_jump_p95_kmh"))
                continue

            reason = _invalid_reason(track)
            na_by_reason[reason] += 1
            if track.get("speed_kmh") is not None and not bool(track.get("physics_valid", False)):
                physics_invalid_by_reason[reason] += 1

    for track_speeds in speeds_by_track.values():
        for previous, current in zip(track_speeds, track_speeds[1:], strict=False):
            speed_jump_values.append(abs(current - previous))

    total = counts["vehicle_track_samples"]
    displayable = counts["displayable_vehicle_track_samples"]
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
        "na_by_reason": dict(sorted(na_by_reason.items())),
        "physics_invalid_by_reason": dict(sorted(physics_invalid_by_reason.items())),
        "fixed_lag_backfill_count": counts["fixed_lag_backfill_count"],
        "frozen_last_valid_count": counts["frozen_last_valid_count"],
        "speed_jump_p95_kmh": _p95(speed_jump_values),
        "max_speed_by_class": dict(sorted(max_speed_by_class.items())),
        "vehicle_speed_display_state_counts": dict(sorted(display_state_counts.items())),
    }


def build_vehicle_speed_aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
    clip_rows: list[dict[str, Any]] = []
    total_samples = 0
    total_displayable = 0
    aggregate_na: Counter[str] = Counter()
    aggregate_invalid: Counter[str] = Counter()
    max_speed_by_class: dict[str, float] = {}
    speed_jump_values: list[float] = []

    for result in results:
        if result.get("status") not in {None, "ok"}:
            continue
        audit = result.get("vehicle_speed_audit")
        if not isinstance(audit, dict):
            continue
        samples = int(audit.get("vehicle_track_samples") or 0)
        displayable = int(audit.get("displayable_vehicle_track_samples") or 0)
        coverage = audit.get("vehicle_display_coverage")
        total_samples += samples
        total_displayable += displayable
        _update_counter(aggregate_na, audit.get("na_by_reason"))
        _update_counter(aggregate_invalid, audit.get("physics_invalid_by_reason"))
        _merge_max_speed(max_speed_by_class, audit.get("max_speed_by_class"))
        _append_float(speed_jump_values, audit.get("speed_jump_p95_kmh"))
        max_car_speed = _max_vehicle_speed(audit)
        clip_rows.append(
            {
                "clip": audit.get("clip") or result.get("clip"),
                "vehicle_track_samples": samples,
                "displayable_vehicle_track_samples": displayable,
                "vehicle_display_coverage": coverage,
                "na_by_reason": audit.get("na_by_reason") or {},
                "physics_invalid_by_reason": audit.get("physics_invalid_by_reason") or {},
                "fixed_lag_backfill_count": int(audit.get("fixed_lag_backfill_count") or 0),
                "frozen_last_valid_count": int(audit.get("frozen_last_valid_count") or 0),
                "speed_jump_p95_kmh": audit.get("speed_jump_p95_kmh"),
                "max_speed_by_class": audit.get("max_speed_by_class") or {},
                "passes_vehicle_speed_acceptance": (
                    coverage is not None
                    and float(coverage) >= CLIP_ACCEPTANCE_MIN_COVERAGE
                    and max_car_speed <= CAR_HARD_MAX_KMH
                ),
            },
        )

    aggregate_coverage = total_displayable / total_samples if total_samples else None
    return {
        "vehicle_track_samples": total_samples,
        "displayable_vehicle_track_samples": total_displayable,
        "vehicle_display_coverage": aggregate_coverage,
        "na_by_reason": dict(sorted(aggregate_na.items())),
        "physics_invalid_by_reason": dict(sorted(aggregate_invalid.items())),
        "fixed_lag_backfill_count": sum(
            int(row["fixed_lag_backfill_count"]) for row in clip_rows
        ),
        "frozen_last_valid_count": sum(
            int(row["frozen_last_valid_count"]) for row in clip_rows
        ),
        "speed_jump_p95_kmh": _p95(speed_jump_values),
        "max_speed_by_class": dict(sorted(max_speed_by_class.items())),
        "clip_rows": clip_rows,
        "dense_city_acceptance_min_coverage": DENSE_CITY_ACCEPTANCE_MIN_COVERAGE,
        "passes_dense_city_acceptance": (
            aggregate_coverage is not None
            and aggregate_coverage >= DENSE_CITY_ACCEPTANCE_MIN_COVERAGE
            and _max_speed_from_mapping(max_speed_by_class) <= CAR_HARD_MAX_KMH
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
) -> dict[str, Any]:
    audit = build_vehicle_speed_audit(
        frame_reports,
        clip=clip,
        processed_video_path=str(processed_video_path) if processed_video_path else None,
        source_commit_value=source_commit_value,
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


def _is_vehicle(track: dict[str, Any]) -> bool:
    try:
        return int(track.get("class_id", -1)) in VEHICLE_CLASS_IDS
    except (TypeError, ValueError):
        return False


def _is_displayable(track: dict[str, Any]) -> bool:
    return track.get("speed_kmh") is not None and bool(track.get("physics_valid", False))


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


def _append_float(values: list[float], value: object) -> None:
    if value is None:
        return
    try:
        values.append(float(value))
    except (TypeError, ValueError):
        return


def _p95(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = int(round((len(ordered) - 1) * 0.95))
    return float(ordered[index] if len(ordered) > 2 else max(ordered, default=median(ordered)))
