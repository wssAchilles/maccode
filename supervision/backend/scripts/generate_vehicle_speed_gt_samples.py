from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from statistics import mean
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from domain.speed.vehicle_diagnostics import annotate_vehicle_speed_reports  # noqa: E402

from scripts.rebuild_vehicle_speed_audits import collect_result_paths  # noqa: E402

GT_SAMPLE_COLUMNS = [
    "clip",
    "tracker_id",
    "frame_start",
    "frame_end",
    "class_name",
    "gt_speed_kmh",
    "source",
    "confidence",
    "audit_priority",
    "audit_reason",
    "frame_mid",
    "predicted_speed_kmh",
    "predicted_uncertainty_kmh",
    "speed_confidence",
    "speed_source",
    "vehicle_speed_display_state",
    "contact_point_source",
    "contact_quality_score",
    "id_switch_risk",
    "notes",
]


def generate_vehicle_speed_gt_samples(
    inputs: list[Path],
    *,
    output_csv: Path,
    max_samples_per_clip: int = 50,
    window_frames: int = 15,
    recursive: bool = False,
    reconstruction_applied: bool = True,
) -> dict[str, Any]:
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    processed = 0
    skipped = 0
    for path in collect_result_paths(inputs, recursive=recursive):
        payload = json.loads(path.read_text(encoding="utf-8"))
        clip = str(payload.get("clip") or path.name)
        frame_reports = payload.get("frame_reports")
        if not isinstance(frame_reports, list) or not frame_reports:
            skipped += 1
            continue
        processed += 1
        annotated = annotate_vehicle_speed_reports(
            frame_reports,
            reconstruction_applied=reconstruction_applied,
        )
        rows.extend(
            _sample_rows_for_clip(
                clip,
                annotated,
                max_samples=max_samples_per_clip,
                window_frames=window_frames,
            ),
        )

    with output_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=GT_SAMPLE_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    summary = {
        "processed_clips": processed,
        "skipped_clips": skipped,
        "sample_count": len(rows),
        "output_csv": str(output_csv),
        "columns": GT_SAMPLE_COLUMNS,
    }
    summary_path = output_csv.with_suffix(".summary.json")
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def _sample_rows_for_clip(
    clip: str,
    frame_reports: list[dict[str, Any]],
    *,
    max_samples: int,
    window_frames: int,
) -> list[dict[str, Any]]:
    displayable_by_track: dict[tuple[int, str], list[dict[str, Any]]] = {}
    hidden_candidates: list[dict[str, Any]] = []
    for fallback_index, report in enumerate(frame_reports):
        frame_index = _frame_index(report, fallback_index)
        for track in report.get("active_tracks", []):
            if not isinstance(track, dict) or not _is_vehicle(track):
                continue
            sample = dict(track)
            sample["frame_index"] = frame_index
            sample["clip"] = clip
            if _is_displayable(sample):
                key = (
                    int(sample.get("tracker_id", -1)),
                    str(sample.get("class_name") or sample.get("class_id")),
                )
                displayable_by_track.setdefault(key, []).append(sample)
            elif _hidden_sample_priority(sample) > 0:
                hidden_candidates.append(sample)

    rows: list[dict[str, Any]] = []
    for samples in displayable_by_track.values():
        ordered = sorted(samples, key=lambda item: int(item["frame_index"]))
        candidate = max(ordered, key=_displayable_sample_priority)
        rows.append(
            _displayable_gt_row(
                clip,
                ordered,
                candidate,
                window_frames=window_frames,
            ),
        )
    rows.extend(_hidden_gt_row(clip, sample) for sample in hidden_candidates)
    rows.sort(
        key=lambda row: (
            -float(row["audit_priority"]),
            str(row["clip"]),
            int(row["frame_mid"]),
            int(row["tracker_id"]),
        ),
    )
    return rows[:max_samples]


def _displayable_gt_row(
    clip: str,
    samples: list[dict[str, Any]],
    candidate: dict[str, Any],
    *,
    window_frames: int,
) -> dict[str, Any]:
    frame_mid = int(candidate["frame_index"])
    half_window = max(1, window_frames // 2)
    frame_start = max(int(samples[0]["frame_index"]), frame_mid - half_window)
    frame_end = min(int(samples[-1]["frame_index"]), frame_mid + half_window)
    selected = [
        sample
        for sample in samples
        if frame_start <= int(sample["frame_index"]) <= frame_end
        and sample.get("speed_kmh") is not None
    ]
    predicted_speeds = [float(sample["speed_kmh"]) for sample in selected]
    uncertainties = [
        float(sample["speed_uncertainty_kmh"])
        for sample in selected
        if _optional_float(sample.get("speed_uncertainty_kmh")) is not None
    ]
    confidences = [
        float(sample["speed_confidence"])
        for sample in selected
        if _optional_float(sample.get("speed_confidence")) is not None
    ]
    return {
        "clip": clip,
        "tracker_id": int(candidate.get("tracker_id", -1)),
        "frame_start": frame_start,
        "frame_end": frame_end,
        "class_name": str(candidate.get("class_name") or candidate.get("class_id")),
        "gt_speed_kmh": "",
        "source": "",
        "confidence": "",
        "audit_priority": round(_displayable_sample_priority(candidate), 6),
        "audit_reason": _displayable_audit_reason(candidate),
        "frame_mid": frame_mid,
        "predicted_speed_kmh": round(mean(predicted_speeds), 6)
        if predicted_speeds
        else "",
        "predicted_uncertainty_kmh": round(mean(uncertainties), 6)
        if uncertainties
        else "",
        "speed_confidence": round(mean(confidences), 6) if confidences else "",
        "speed_source": str(candidate.get("speed_source") or "measured"),
        "vehicle_speed_display_state": str(
            candidate.get("vehicle_speed_display_state") or "unknown",
        ),
        "contact_point_source": str(candidate.get("contact_point_source") or "unknown"),
        "contact_quality_score": _round_or_blank(candidate.get("contact_point_quality_score")),
        "id_switch_risk": _round_or_blank(candidate.get("id_switch_risk")),
        "notes": "fill gt_speed_kmh from manual timing or trusted reference",
    }


def _hidden_gt_row(clip: str, sample: dict[str, Any]) -> dict[str, Any]:
    frame_index = int(sample["frame_index"])
    return {
        "clip": clip,
        "tracker_id": int(sample.get("tracker_id", -1)),
        "frame_start": frame_index,
        "frame_end": frame_index,
        "class_name": str(sample.get("class_name") or sample.get("class_id")),
        "gt_speed_kmh": "",
        "source": "",
        "confidence": "",
        "audit_priority": round(_hidden_sample_priority(sample), 6),
        "audit_reason": _hidden_audit_reason(sample),
        "frame_mid": frame_index,
        "predicted_speed_kmh": _round_or_blank(sample.get("speed_kmh")),
        "predicted_uncertainty_kmh": _round_or_blank(sample.get("speed_uncertainty_kmh")),
        "speed_confidence": _round_or_blank(sample.get("speed_confidence")),
        "speed_source": str(sample.get("speed_source") or "none"),
        "vehicle_speed_display_state": str(
            sample.get("vehicle_speed_display_state") or "unknown",
        ),
        "contact_point_source": str(sample.get("contact_point_source") or "unknown"),
        "contact_quality_score": _round_or_blank(sample.get("contact_point_quality_score")),
        "id_switch_risk": _round_or_blank(sample.get("id_switch_risk")),
        "notes": "review hidden speed state before adding gt_speed_kmh",
    }


def _displayable_sample_priority(sample: dict[str, Any]) -> float:
    priority = 1.0
    source = str(sample.get("speed_source") or "")
    if source.startswith("fixed_lag"):
        priority += 3.0
    if bool(sample.get("speed_uncertainty_recalibrated")):
        priority += 3.0
    if bool(sample.get("id_switch_risk_downgraded")):
        priority += 4.0
    uncertainty = _optional_float(sample.get("speed_uncertainty_kmh"))
    if uncertainty is not None:
        priority += min(4.0, uncertainty / 8.0)
    confidence = _optional_float(sample.get("speed_confidence"))
    if confidence is not None and confidence < 0.35:
        priority += 2.0
    contact_quality = _optional_float(sample.get("contact_point_quality_score"))
    if contact_quality is not None and contact_quality < 0.45:
        priority += 2.0
    if bool(sample.get("bbox_center_fallback")):
        priority += 2.0
    priority += min(2.0, _id_switch_risk(sample) * 2.0)
    return priority


def _displayable_audit_reason(sample: dict[str, Any]) -> str:
    if bool(sample.get("id_switch_risk_downgraded")):
        return "id_switch_risk_downgraded"
    if bool(sample.get("speed_uncertainty_recalibrated")):
        return "rts_uncertainty_recalibrated"
    source = str(sample.get("speed_source") or "")
    if source.startswith("fixed_lag"):
        return "fixed_lag_speed"
    if bool(sample.get("bbox_center_fallback")):
        return "bbox_center_fallback"
    return "calibration_sample"


def _hidden_sample_priority(sample: dict[str, Any]) -> float:
    if _id_switch_risk(sample) >= 0.7:
        return 20.0 + _id_switch_risk(sample)
    if sample.get("vehicle_speed_display_state") == "warming_up_hidden":
        return 8.0
    return 0.0


def _hidden_audit_reason(sample: dict[str, Any]) -> str:
    if _id_switch_risk(sample) >= 0.7:
        return "hidden_id_switch_risk"
    if sample.get("vehicle_speed_display_state") == "warming_up_hidden":
        return "unresolved_warmup_hidden"
    return "hidden_speed"


def _is_vehicle(track: dict[str, Any]) -> bool:
    try:
        return int(track.get("class_id", -1)) in {2, 3, 5, 7}
    except (TypeError, ValueError):
        return False


def _is_displayable(track: dict[str, Any]) -> bool:
    return track.get("speed_kmh") is not None and bool(track.get("physics_valid", False))


def _id_switch_risk(track: dict[str, Any]) -> float:
    value = _optional_float(track.get("id_switch_risk"))
    return value if value is not None else 0.0


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _round_or_blank(value: object) -> float | str:
    numeric = _optional_float(value)
    return round(numeric, 6) if numeric is not None else ""


def _frame_index(report: dict[str, Any], fallback_index: int) -> int:
    try:
        return int(report.get("frame_index", fallback_index))
    except (TypeError, ValueError):
        return fallback_index


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate manual vehicle speed GT audit CSV samples from result JSONs.",
    )
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=Path("data/outputs/vehicle_speed_diagnostics/manual_gt_samples.csv"),
    )
    parser.add_argument("--max-samples-per-clip", type=int, default=50)
    parser.add_argument("--window-frames", type=int, default=15)
    parser.add_argument("--recursive", action="store_true")
    parser.add_argument(
        "--reconstruction-applied",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = generate_vehicle_speed_gt_samples(
        list(args.inputs),
        output_csv=args.output_csv,
        max_samples_per_clip=max(1, int(args.max_samples_per_clip)),
        window_frames=max(1, int(args.window_frames)),
        recursive=bool(args.recursive),
        reconstruction_applied=bool(args.reconstruction_applied),
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
