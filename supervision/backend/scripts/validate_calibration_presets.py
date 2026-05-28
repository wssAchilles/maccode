from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from domain.calibration.service import CalibrationService

from scripts.analyze_real_videos import load_calibration_presets


def validate_catalog(
    path: Path,
    required_clips: list[str] | None = None,
) -> dict[str, Any]:
    catalog = load_calibration_presets(path)
    rows: list[dict[str, Any]] = []
    required = required_clips or []
    for clip, preset in sorted(catalog.video_calibrations.items()):
        issues: list[str] = []
        if len(preset.points) < 4:
            issues.append("too_few_points")
        if preset.position_rmse_floor_m <= 0:
            issues.append("invalid_position_rmse_floor")
        if preset.calibration_scale_uncertainty_pct <= 0:
            issues.append("invalid_scale_uncertainty")
        if "replace" in preset.notes.lower() or "template" in preset.notes.lower():
            issues.append("template_points_not_manual")

        homography = None
        if not issues:
            try:
                homography = CalibrationService().compute_homography_ransac(
                    preset.points,
                    random_seed=11,
                )
            except ValueError as exc:
                issues.append(str(exc))

        if homography is not None:
            if homography.calibration_quality == "unstable":
                issues.append("unstable_homography")
            if homography.reprojection_rmse > preset.position_rmse_floor_m:
                issues.append("rmse_exceeds_floor")
        rows.append(
            {
                "clip": clip,
                "status": "pass" if not issues else "fail",
                "issues": issues,
                "point_count": len(preset.points),
                "position_rmse_floor_m": preset.position_rmse_floor_m,
                "scale_uncertainty_pct": preset.calibration_scale_uncertainty_pct,
                "calibration_quality": (
                    homography.calibration_quality if homography is not None else None
                ),
                "reprojection_rmse": (
                    homography.reprojection_rmse if homography is not None else None
                ),
                "inlier_count": homography.inlier_count if homography is not None else None,
                "required": clip in required,
            },
        )
    calibrated_clips = {row["clip"] for row in rows if row["status"] == "pass"}
    missing_required = [clip for clip in required if clip not in calibrated_clips]
    readiness_issues = []
    if missing_required:
        readiness_issues.append("missing_required_video_calibration")
    if any(row["status"] == "fail" and row["required"] for row in rows):
        readiness_issues.append("required_video_calibration_failed")
    return {
        "preset_path": str(path),
        "video_calibration_count": len(rows),
        "pass_count": sum(1 for row in rows if row["status"] == "pass"),
        "fail_count": sum(1 for row in rows if row["status"] == "fail"),
        "required_clips": required,
        "missing_required_clips": missing_required,
        "industrial_readiness": "ready" if not readiness_issues else "not_ready",
        "readiness_issues": readiness_issues,
        "rows": rows,
    }


def render_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Calibration Preset Validation",
        "",
        f"- Preset path: `{summary['preset_path']}`",
        f"- Video calibrations: {summary['video_calibration_count']}",
        f"- Pass: {summary['pass_count']}",
        f"- Fail: {summary['fail_count']}",
        f"- Industrial readiness: `{summary['industrial_readiness']}`",
        "",
        "| Clip | Status | Points | Quality | RMSE | Issues |",
        "| --- | --- | ---: | --- | ---: | --- |",
    ]
    for row in summary["rows"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    row["clip"],
                    row["status"],
                    str(row["point_count"]),
                    str(row["calibration_quality"] or "N/A"),
                    (
                        "N/A"
                        if row["reprojection_rmse"] is None
                        else f"{row['reprojection_rmse']:.4f}"
                    ),
                    ", ".join(row["issues"]) if row["issues"] else "none",
                ],
            )
            + " |",
        )
    if summary["missing_required_clips"]:
        lines.extend(
            [
                "",
                "## Missing Required Manual Calibrations",
                "",
            ],
        )
        for clip in summary["missing_required_clips"]:
            lines.append(f"- `{clip}`")
    if not summary["rows"]:
        lines.extend(
            [
                "",
                "No per-video manual calibration presets are configured yet.",
                (
                    "Scene-profile calibration can run demos, but it is not "
                    "engineering-grade speed calibration."
                ),
            ],
        )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate per-video calibration presets.")
    parser.add_argument("--input", default="data/tests/calibration_presets.json")
    parser.add_argument("--output-dir", default="data/outputs/calibration_validation")
    parser.add_argument(
        "--required-clips",
        nargs="*",
        default=None,
        help="Exact MP4 filenames that must have passing per-video calibration presets.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = validate_catalog(Path(args.input), required_clips=args.required_clips)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "calibration_validation.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
    )
    (output_dir / "calibration_validation.md").write_text(render_markdown(summary))
    print(
        json.dumps(
            {
                "video_calibrations": summary["video_calibration_count"],
                "pass": summary["pass_count"],
                "fail": summary["fail_count"],
                "industrial_readiness": summary["industrial_readiness"],
                "output_dir": str(output_dir),
            },
            ensure_ascii=False,
            indent=2,
        ),
    )


if __name__ == "__main__":
    main()
