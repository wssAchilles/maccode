from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from domain.speed.vehicle_diagnostics import (  # noqa: E402
    annotate_vehicle_speed_reports,
    build_vehicle_speed_audit,
)

from scripts.rebuild_vehicle_speed_audits import collect_result_paths  # noqa: E402


def build_vehicle_3d_speed_qa(
    inputs: list[Path],
    *,
    output_dir: Path,
    recursive: bool = False,
    reconstruction_applied: bool = True,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    clip_rows: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    for path in collect_result_paths(inputs, recursive=recursive):
        payload = json.loads(path.read_text(encoding="utf-8"))
        clip = str(payload.get("clip") or path.name)
        frame_reports = payload.get("frame_reports")
        if not isinstance(frame_reports, list) or not frame_reports:
            skipped.append(
                {
                    "clip": clip,
                    "source_result_path": str(path),
                    "reason": "missing_frame_reports",
                },
            )
            continue
        annotated = annotate_vehicle_speed_reports(
            frame_reports,
            reconstruction_applied=reconstruction_applied,
        )
        audit = build_vehicle_speed_audit(annotated, clip=clip)
        clip_rows.append(_clip_qa_row(clip, path, audit))

    payload = {
        "source_inputs": [str(path) for path in inputs],
        "output_dir": str(output_dir),
        "clip_count": len(clip_rows),
        "skipped_count": len(skipped),
        "skipped": skipped,
        "aggregate": _aggregate_qa_rows(clip_rows),
        "clips": clip_rows,
    }
    (output_dir / "vehicle_3d_speed_qa.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "vehicle_3d_speed_qa.md").write_text(
        render_vehicle_3d_speed_qa_markdown(payload),
        encoding="utf-8",
    )
    return payload


def _clip_qa_row(
    clip: str,
    source_path: Path,
    audit: dict[str, Any],
) -> dict[str, Any]:
    sanity = audit.get("vehicle_3d_scale_sanity")
    if not isinstance(sanity, dict):
        sanity = {"available": False, "reason": "missing_vehicle_3d_scale_sanity"}
    calibration_3d = _calibration_3d_from_sanity(sanity)
    y_depth_bias = sanity.get("scale_bias_by_y_depth")
    lane_bias = sanity.get("scale_bias_by_lane_zone")
    return {
        "clip": clip,
        "source_result_path": str(source_path),
        "vehicle_display_coverage": audit.get("vehicle_display_coverage"),
        "safe_vehicle_display_coverage": audit.get("safe_vehicle_display_coverage"),
        "vehicle_3d_scale_sanity_available": bool(sanity.get("available")),
        "calibration_3d_available": bool(sanity.get("calibration_3d_available")),
        "calibration_3d_source": calibration_3d.get("calibration_source"),
        "calibration_3d_quality": calibration_3d.get("calibration_quality"),
        "calibration_3d_trusted": calibration_3d.get("calibration_trusted"),
        "calibration_3d_quality_issues": calibration_3d.get("quality_issues") or [],
        "scale_bias_by_y_depth": y_depth_bias if isinstance(y_depth_bias, dict) else {},
        "scale_bias_by_lane_zone": lane_bias if isinstance(lane_bias, dict) else {},
        "bbox_size_consistency_error": sanity.get("bbox_size_consistency_error"),
        "homography_uncertainty_multiplier": sanity.get(
            "homography_uncertainty_multiplier",
        ),
        "calibration_region_quality": sanity.get("calibration_region_quality"),
        "recommended_action": _recommended_action(sanity),
    }


def _aggregate_qa_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    quality_counts: Counter[str] = Counter(
        str(row.get("calibration_region_quality") or "unknown") for row in rows
    )
    calibration_quality_counts: Counter[str] = Counter(
        str(row.get("calibration_3d_quality") or "unknown") for row in rows
    )
    calibration_source_counts: Counter[str] = Counter(
        str(row.get("calibration_3d_source") or "unknown") for row in rows
    )
    multipliers = [
        float(row["homography_uncertainty_multiplier"])
        for row in rows
        if _is_number(row.get("homography_uncertainty_multiplier"))
    ]
    bbox_errors = [
        float(row["bbox_size_consistency_error"])
        for row in rows
        if _is_number(row.get("bbox_size_consistency_error"))
    ]
    review_clips = [
        row["clip"]
        for row in rows
        if row.get("calibration_region_quality") in {"review", "poor"}
    ]
    return {
        "clip_count": len(rows),
        "vehicle_3d_scale_sanity_available_count": sum(
            1 for row in rows if row.get("vehicle_3d_scale_sanity_available")
        ),
        "calibration_3d_available_count": sum(
            1 for row in rows if row.get("calibration_3d_available")
        ),
        "calibration_region_quality_counts": dict(sorted(quality_counts.items())),
        "calibration_3d_quality_counts": dict(sorted(calibration_quality_counts.items())),
        "calibration_3d_source_counts": dict(sorted(calibration_source_counts.items())),
        "mean_homography_uncertainty_multiplier": (
            mean(multipliers) if multipliers else None
        ),
        "max_homography_uncertainty_multiplier": max(multipliers, default=None),
        "mean_bbox_size_consistency_error": mean(bbox_errors) if bbox_errors else None,
        "review_clip_count": len(review_clips),
        "review_clips": review_clips,
        "model_reference": "vehicle_3d_prior_speed_qa_v1",
    }


def _calibration_3d_from_sanity(sanity: dict[str, Any]) -> dict[str, Any]:
    value = sanity.get("calibration_3d_diagnostics")
    if isinstance(value, dict):
        return value
    return {}


def _recommended_action(sanity: dict[str, Any]) -> str:
    if not sanity.get("available"):
        return "collect_vehicle_tracks_for_scale_sanity"
    quality = str(sanity.get("calibration_region_quality") or "unknown")
    if quality == "poor":
        return "review_local_homography_or_metric_plane_before_trusting_speed"
    if quality == "review":
        return "increase_region_uncertainty_or_add_gt_speed_samples"
    if not sanity.get("calibration_3d_available"):
        return "add_vehicle_3d_priors_or_bbox_observations_for_offline_qa"
    return "none"


def render_vehicle_3d_speed_qa_markdown(payload: dict[str, Any]) -> str:
    aggregate = payload.get("aggregate") or {}
    lines = [
        "# Vehicle 3D Speed QA",
        "",
        f"- Clips: {payload.get('clip_count', 0)}",
        f"- Skipped: {payload.get('skipped_count', 0)}",
        (
            "- 3D scale sanity available: "
            f"{aggregate.get('vehicle_3d_scale_sanity_available_count', 0)}"
        ),
        (
            "- 3D calibration diagnostics available: "
            f"{aggregate.get('calibration_3d_available_count', 0)}"
        ),
        (
            "- Mean homography uncertainty multiplier: "
            f"{_fmt(aggregate.get('mean_homography_uncertainty_multiplier'))}"
        ),
        f"- Review clips: {aggregate.get('review_clip_count', 0)}",
        "",
        "| Clip | Region quality | 3D quality | Multiplier | BBox size error | Action |",
        "| --- | --- | --- | ---: | ---: | --- |",
    ]
    for row in payload.get("clips", []):
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row.get("clip")),
                    str(row.get("calibration_region_quality")),
                    str(row.get("calibration_3d_quality")),
                    _fmt(row.get("homography_uncertainty_multiplier")),
                    _fmt(row.get("bbox_size_consistency_error")),
                    str(row.get("recommended_action")),
                ],
            )
            + " |",
        )
    lines.append("")
    return "\n".join(lines)


def _fmt(value: object) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, int | float):
        return f"{float(value):.4f}"
    return str(value)


def _is_number(value: object) -> bool:
    return isinstance(value, int | float)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build offline vehicle 3D prior speed QA from result JSON frame reports.",
    )
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/outputs/vehicle_3d_speed_qa"),
    )
    parser.add_argument("--recursive", action="store_true")
    parser.add_argument(
        "--reconstruction-applied",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_vehicle_3d_speed_qa(
        list(args.inputs),
        output_dir=args.output_dir,
        recursive=bool(args.recursive),
        reconstruction_applied=bool(args.reconstruction_applied),
    )
    print(
        json.dumps(
            {
                "clips": payload["clip_count"],
                "skipped": payload["skipped_count"],
                "output_dir": payload["output_dir"],
                "review_clip_count": payload["aggregate"]["review_clip_count"],
            },
            ensure_ascii=False,
            indent=2,
        ),
    )


if __name__ == "__main__":
    main()
