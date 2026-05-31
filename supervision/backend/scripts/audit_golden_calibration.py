from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


GOLDEN_CLIPS = {
    "026_complex_signal_day_wide_0115s_30s.mp4",
    "042_pedestrian_crowd_high_view_0270s_30s.mp4",
    "054_dense_city_traffic_4k_elevated_0030s_30s.mp4",
    "058_dense_city_traffic_4k_elevated_0150s_30s.mp4",
}
TRUST_GATE_PX = 15.0
MIN_INDEPENDENT_VALIDATION_SEGMENTS = 2
MIN_RECOMMENDED_CONTROL_POINTS = 8
TRUSTED_SOURCES = {"video_manual_preset", "camera_manual_preset"}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_path(project_root: Path, value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value)
    return path if path.is_absolute() else project_root / path


def audit_clip(row: dict[str, Any], project_root: Path) -> dict[str, Any]:
    issues: list[str] = []
    warnings: list[str] = []
    clip = str(row.get("clip"))
    trusted = bool(row.get("calibration_trusted"))
    source = row.get("calibration_source")
    validation = row.get("validation_max_error_px")
    independent_segments = int(row.get("independent_validation_segment_count") or 0)
    grid_rendered = bool(row.get("homography_grid_rendered"))
    provenance_issues = [
        str(issue) for issue in row.get("provenance_issues", []) if str(issue).strip()
    ]

    if source not in TRUSTED_SOURCES:
        issues.append(f"invalid calibration_source for grid: {source}")
    if row.get("provenance_trusted") is False:
        issues.extend(provenance_issues or ["calibration provenance is not trusted"])
    if not trusted:
        issues.append("calibration is not trusted")
    if validation is None:
        issues.append("missing validation_max_error_px")
    elif float(validation) > TRUST_GATE_PX:
        issues.append(
            f"validation error {float(validation):.2f}px exceeds "
            f"{TRUST_GATE_PX:.0f}px gate",
        )
    if independent_segments < MIN_INDEPENDENT_VALIDATION_SEGMENTS:
        issues.append(
            "requires at least "
            f"{MIN_INDEPENDENT_VALIDATION_SEGMENTS} independent validation segments",
        )
    if trusted and not grid_rendered:
        issues.append("trusted calibration did not render Homography Grid")
    if not trusted and grid_rendered:
        issues.append("untrusted calibration rendered Homography Grid")

    if not row.get("calibration_pipeline_consistent", False):
        issues.append("QA calibration source/trust does not match analysis output")

    for key in ("qa_image", "processed_mp4", "math_model_card_md", "frame_report_json"):
        artifact_path = resolve_path(project_root, row.get(key))
        if artifact_path is None or not artifact_path.exists():
            issues.append(f"missing artifact: {key}")

    point_count = int(row.get("point_count") or 0)
    if point_count < MIN_RECOMMENDED_CONTROL_POINTS:
        issues.append(
            "requires 8-10 manual control points for golden calibration; "
            f"found {point_count}",
        )
    if not bool(row.get("has_scale_prior")):
        issues.append("missing scale_prior meter anchor")
    if not bool(row.get("has_profile_notes")):
        issues.append("missing profile_notes")
    if not bool(row.get("has_road_plane_polygon_pixel")):
        issues.append("missing road_plane_polygon_pixel")
    if not bool(row.get("has_road_plane_polygon_world")):
        issues.append("missing road_plane_polygon_world")

    if point_count < 6:
        warnings.append("fewer than 6 manual control points")
    elif point_count < MIN_RECOMMENDED_CONTROL_POINTS:
        warnings.append("fewer than recommended 8 manual control points")
    if independent_segments < MIN_INDEPENDENT_VALIDATION_SEGMENTS:
        warnings.append("not enough independent validation segments")
    if validation is not None and float(validation) > TRUST_GATE_PX:
        warnings.append("validation error still exceeds usable gate")

    return {
        "clip": clip,
        "defense_ready": trusted and grid_rendered and not issues,
        "calibration_source": source,
        "calibration_trusted": trusted,
        "provenance_trusted": row.get("provenance_trusted"),
        "provenance_issues": provenance_issues,
        "validation_max_error_px": validation,
        "independent_validation_segment_count": independent_segments,
        "point_count": point_count,
        "has_scale_prior": bool(row.get("has_scale_prior")),
        "has_profile_notes": bool(row.get("has_profile_notes")),
        "has_road_plane_polygon_pixel": bool(row.get("has_road_plane_polygon_pixel")),
        "has_road_plane_polygon_world": bool(row.get("has_road_plane_polygon_world")),
        "homography_grid_rendered": grid_rendered,
        "issues": issues,
        "warnings": warnings,
    }


def audit_acceptance_table(
    acceptance: dict[str, Any],
    *,
    project_root: Path,
) -> dict[str, Any]:
    rows = acceptance.get("clips", [])
    by_clip = {str(row.get("clip")): row for row in rows}
    missing = sorted(GOLDEN_CLIPS.difference(by_clip))
    unexpected = sorted(set(by_clip).difference(GOLDEN_CLIPS))
    clip_audits = [
        audit_clip(by_clip[clip], project_root)
        for clip in sorted(GOLDEN_CLIPS & set(by_clip))
    ]
    global_issues: list[str] = []
    if missing:
        global_issues.append(f"missing golden clips: {', '.join(missing)}")
    if unexpected:
        global_issues.append(f"unexpected clips in acceptance table: {', '.join(unexpected)}")
    if any(row["issues"] for row in clip_audits):
        global_issues.append("one or more golden clips failed calibration audit")
    ready_count = sum(1 for row in clip_audits if row["defense_ready"])
    return {
        "clip_count": len(clip_audits),
        "required_clip_count": len(GOLDEN_CLIPS),
        "defense_ready_count": ready_count,
        "all_defense_ready": (
            ready_count == len(GOLDEN_CLIPS)
            and not global_issues
            and not missing
            and not unexpected
        ),
        "global_issues": global_issues,
        "clips": clip_audits,
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Golden Calibration Audit",
        "",
        (
            "- Defense-ready clips: "
            f"`{payload['defense_ready_count']}/{payload['required_clip_count']}`"
        ),
        f"- All defense-ready: `{payload['all_defense_ready']}`",
        "",
        (
            "| Clip | Ready | Source | Trusted | Points | Validation | "
            "Independent Segments | Grid | Issues |"
        ),
        "| --- | --- | --- | --- | ---: | ---: | ---: | --- | --- |",
    ]
    for row in payload["clips"]:
        validation = row["validation_max_error_px"]
        lines.append(
            "| "
            + " | ".join(
                [
                    row["clip"],
                    str(row["defense_ready"]),
                    str(row["calibration_source"]),
                    str(row["calibration_trusted"]),
                    str(row["point_count"]),
                    "N/A" if validation is None else f"{float(validation):.2f}px",
                    str(row["independent_validation_segment_count"]),
                    str(row["homography_grid_rendered"]),
                    "<br>".join(row["issues"]) if row["issues"] else "none",
                ],
            )
            + " |",
        )
    if payload["global_issues"]:
        lines.extend(["", "## Global Issues", ""])
        lines.extend(f"- {issue}" for issue in payload["global_issues"])
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit the four golden clips against the defense calibration gate.",
    )
    parser.add_argument(
        "--acceptance-table",
        default="data/outputs/golden_acceptance_table/golden_acceptance_table.json",
    )
    parser.add_argument("--output-dir", default="data/outputs/golden_calibration_audit")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with status 1 unless all four clips are defense-ready.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    project_root = Path.cwd()
    payload = audit_acceptance_table(
        load_json(Path(args.acceptance_table)),
        project_root=project_root,
    )
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "golden_calibration_audit.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "golden_calibration_audit.md").write_text(
        render_markdown(payload),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "defense_ready_count": payload["defense_ready_count"],
                "required_clip_count": payload["required_clip_count"],
                "all_defense_ready": payload["all_defense_ready"],
                "output_dir": str(output_dir),
            },
            ensure_ascii=False,
            indent=2,
        ),
    )
    if args.strict and not payload["all_defense_ready"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
