from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


IDEAL_VALIDATION_ERROR_PX = 8.0
USABLE_VALIDATION_ERROR_PX = 15.0
MIN_INDEPENDENT_VALIDATION_SEGMENTS = 2
MIN_RECOMMENDED_CONTROL_POINTS = 8


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def readiness_level(row: dict[str, Any]) -> str:
    if row.get("calibration_trusted") and row.get("homography_grid_rendered"):
        validation = row.get("validation_max_error_px")
        if validation is not None and validation < IDEAL_VALIDATION_ERROR_PX:
            return "trusted_ideal"
        return "trusted_usable"
    return "needs_manual_refinement"


def required_actions(row: dict[str, Any]) -> list[str]:
    actions: list[str] = []
    point_count = int(row.get("point_count") or 0)
    segment_count = int(row.get("validation_segment_count") or 0)
    independent_segment_count = int(row.get("independent_validation_segment_count") or 0)
    validation = row.get("validation_max_error_px")
    if row.get("calibration_source") == "scene_profile_preset":
        actions.append(
            "create video_manual_preset or camera_manual_preset; "
            "scene presets cannot render grid",
        )
    if row.get("provenance_trusted") is False:
        actions.append(
            "replace visual/automatic prior evidence with real manual ground-control "
            "points and a measured meter scale anchor",
        )
    if point_count < 6:
        actions.append("collect at least 6 real non-collinear same-plane ground control points")
    if point_count < MIN_RECOMMENDED_CONTROL_POINTS:
        actions.append("collect at least 8 control points for the four golden defense clips")
    if point_count < 10:
        actions.append("prefer 8-10 control points spread across near, middle, and far road plane")
    if not row.get("has_scale_prior"):
        actions.append("record scale_prior meter anchor such as surveyed lane/crosswalk width")
    if not row.get("has_profile_notes"):
        actions.append("add profile_notes explaining fixed camera, ground plane, and scale prior")
    if not row.get("has_road_plane_polygon_pixel") or not row.get(
        "has_road_plane_polygon_world",
    ):
        actions.append("add road_plane_polygon_pixel and road_plane_polygon_world bounds")
    if segment_count < MIN_INDEPENDENT_VALIDATION_SEGMENTS:
        actions.append(
            "add at least 2 independent validation_segments not reused as control points",
        )
    if independent_segment_count < MIN_INDEPENDENT_VALIDATION_SEGMENTS:
        actions.append(
            "replace or add validation_segments until at least 2 independent road "
            "markings pass validation",
        )
    if validation is None:
        actions.append(
            "measure independent validation segments such as lane lines, "
            "stop lines, or pavement edges",
        )
    elif validation > USABLE_VALIDATION_ERROR_PX:
        actions.append(
            "re-pick control/validation geometry; "
            f"validation error {validation:.2f}px exceeds 15px gate",
        )
    if not row.get("declared_trusted"):
        actions.append("keep calibration_trusted=false until independent validation passes")
    if row.get("calibration_trusted") and not row.get("homography_grid_rendered"):
        actions.append("investigate trusted/grid mismatch before using this sample in defense")
    if not row.get("calibration_pipeline_consistent", True):
        actions.append("fix QA and analysis calibration source mismatch")
    return actions


def camera_profile_reuse_target(clip: str) -> str:
    if clip.startswith("026_") or clip.startswith("023_"):
        return "jackson_hole_signal_camera"
    if clip.startswith("042_") or "_pedestrian_crowd_high_view_" in clip:
        return "pedestrian_high_view_camera"
    if clip.startswith(("054_", "058_")) or "_dense_city_traffic_4k_elevated_" in clip:
        return "dense_city_4k_camera"
    return "new_camera_profile"


def build_readiness_report(acceptance_path: Path, output_dir: Path) -> dict[str, Any]:
    acceptance = load_json(acceptance_path)
    clips = []
    for row in acceptance["clips"]:
        level = readiness_level(row)
        actions = required_actions(row)
        clips.append(
            {
                "clip": row["clip"],
                "readiness": level,
                "camera_profile_reuse_target": camera_profile_reuse_target(row["clip"]),
                "calibration_source": row.get("calibration_source"),
                "calibration_trusted": row.get("calibration_trusted"),
                "provenance_trusted": row.get("provenance_trusted"),
                "provenance_issues": row.get("provenance_issues", []),
                "validation_max_error_px": row.get("validation_max_error_px"),
                "homography_grid_rendered": row.get("homography_grid_rendered"),
                "point_count": row.get("point_count"),
                "validation_segment_count": row.get("validation_segment_count"),
                "has_scale_prior": row.get("has_scale_prior"),
                "has_profile_notes": row.get("has_profile_notes"),
                "has_road_plane_polygon_pixel": row.get("has_road_plane_polygon_pixel"),
                "has_road_plane_polygon_world": row.get("has_road_plane_polygon_world"),
                "independent_validation_segment_count": row.get(
                    "independent_validation_segment_count",
                ),
                "qa_image": row.get("qa_image"),
                "processed_mp4": row.get("processed_mp4"),
                "math_model_card_md": row.get("math_model_card_md"),
                "actions": actions,
            },
        )
    payload = {
        "acceptance_table": str(acceptance_path),
        "clip_count": len(clips),
        "trusted_count": sum(1 for row in clips if row["calibration_trusted"]),
        "ready_for_defense_count": sum(
            1 for row in clips if row["readiness"].startswith("trusted_")
        ),
        "clips": clips,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "calibration_readiness_report.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
    )
    (output_dir / "calibration_readiness_report.md").write_text(render_markdown(payload))
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Calibration Readiness Report",
        "",
        f"- Acceptance table: `{payload['acceptance_table']}`",
        f"- Trusted clips: `{payload['trusted_count']}/{payload['clip_count']}`",
        f"- Defense-ready clips: `{payload['ready_for_defense_count']}/{payload['clip_count']}`",
        (
            "- Promotion command after validation: "
            "`python backend/scripts/promote_video_calibration_to_camera_profile.py --write`"
        ),
        "",
        "| Clip | Readiness | Reuse Target | Validation | Grid | Actions |",
        "| --- | --- | --- | ---: | --- | --- |",
    ]
    for row in payload["clips"]:
        validation = row["validation_max_error_px"]
        actions = "<br>".join(row["actions"]) if row["actions"] else "none"
        lines.append(
            "| "
            + " | ".join(
                [
                    row["clip"],
                    row["readiness"],
                    row["camera_profile_reuse_target"],
                    "N/A" if validation is None else f"{validation:.2f}px",
                    str(row["homography_grid_rendered"]),
                    actions,
                ],
            )
            + " |",
        )
    lines.extend(["", "## Per-Clip Evidence", ""])
    for row in payload["clips"]:
        lines.append(f"### {row['clip']}")
        lines.append(f"- QA image: `{row['qa_image']}`")
        lines.append(f"- Processed MP4: `{row['processed_mp4']}`")
        lines.append(f"- Math model card: `{row['math_model_card_md']}`")
        lines.append(
            "- Profile reuse target after validation: "
            f"`{row['camera_profile_reuse_target']}`",
        )
        lines.append(
            "- Promotion command: "
            "`python backend/scripts/promote_video_calibration_to_camera_profile.py "
            f"--clips {row['clip']} --write`",
        )
        if row["actions"]:
            lines.append("- Required actions:")
            lines.extend(f"  - {action}" for action in row["actions"])
        lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a concrete readiness checklist for golden calibration clips.",
    )
    parser.add_argument(
        "--acceptance-table",
        default="data/outputs/golden_acceptance_table/golden_acceptance_table.json",
    )
    parser.add_argument("--output-dir", default="data/outputs/calibration_readiness")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_readiness_report(
        acceptance_path=Path(args.acceptance_table),
        output_dir=Path(args.output_dir),
    )
    print(
        json.dumps(
            {
                "clip_count": payload["clip_count"],
                "trusted_count": payload["trusted_count"],
                "ready_for_defense_count": payload["ready_for_defense_count"],
                "output_dir": args.output_dir,
            },
            ensure_ascii=False,
            indent=2,
        ),
    )


if __name__ == "__main__":
    main()
