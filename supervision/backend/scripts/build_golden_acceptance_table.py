from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


TRUST_GATE_PX = 15.0
MIN_INDEPENDENT_VALIDATION_SEGMENTS = 2
MIN_RECOMMENDED_CONTROL_POINTS = 8


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def validation_status(validation_error_px: float | None, trusted: bool) -> tuple[str, str]:
    if trusted:
        return "trusted", "independent validation passed"
    if validation_error_px is None:
        return "needs_manual_refinement", "missing independent validation_segments"
    if validation_error_px > TRUST_GATE_PX:
        return (
            "needs_manual_refinement",
            f"validation_max_error_px {validation_error_px:.2f} > {TRUST_GATE_PX:.0f}",
        )
    return "needs_manual_refinement", "calibration was not declared trusted"


def scene_priority(final_report: dict[str, Any]) -> str:
    people = final_report.get("regional_people_count") or {}
    traffic_flow = final_report.get("traffic_flow") or {}
    people_count = int(people.get("people_count") or 0)
    active_tracks = final_report.get("active_tracks") or []
    vehicle_count = sum(
        1
        for track in active_tracks
        if str(track.get("class_name", "")).lower() in {"car", "bus", "truck", "motorcycle"}
    )
    if people_count >= vehicle_count:
        level = people.get("crowding_level", "unknown")
        density = people.get("density_people_per_sqm")
        return f"people/density first, crowding={level}, density={density}"
    congestion = traffic_flow.get("congestion_level", "unknown")
    flow = traffic_flow.get("flow_q_veh_per_hour")
    return f"vehicle speed/flow first, congestion={congestion}, flow={flow}"


def build_row(
    qa_row: dict[str, Any],
    analysis_row: dict[str, Any],
    analysis_dir: Path,
) -> dict[str, Any]:
    clip_name = qa_row["clip"]
    clip_stem = Path(clip_name).stem
    final_report = analysis_row.get("final_report") or {}
    processed_video = analysis_row.get("processed_video") or {}
    analysis_calibration = analysis_row.get("calibration") or {}
    processed_path = Path(processed_video.get("path", ""))
    math_card_dir = analysis_dir / "math_model_cards" / clip_stem
    validation_error = qa_row.get("validation_max_error_px")
    status, reason = validation_status(validation_error, bool(qa_row.get("calibration_trusted")))
    independent_segment_count = int(qa_row.get("independent_validation_segment_count") or 0)
    if independent_segment_count < MIN_INDEPENDENT_VALIDATION_SEGMENTS:
        status = "needs_manual_refinement"
        reason = (
            "at least 2 independent validation_segments are required; "
            f"found {independent_segment_count}"
        )
    point_count = int(qa_row.get("point_count") or 0)
    has_scale_prior = bool(qa_row.get("has_scale_prior"))
    has_road_plane_polygon_pixel = bool(qa_row.get("has_road_plane_polygon_pixel"))
    has_road_plane_polygon_world = bool(qa_row.get("has_road_plane_polygon_world"))
    has_profile_notes = bool(qa_row.get("has_profile_notes"))
    if point_count < MIN_RECOMMENDED_CONTROL_POINTS:
        status = "needs_manual_refinement"
        reason = (
            "8-10 manual_control_points are required for golden calibration; "
            f"found {point_count}"
        )
    if not has_scale_prior:
        status = "needs_manual_refinement"
        reason = "missing scale_prior meter anchor"
    if not has_profile_notes:
        status = "needs_manual_refinement"
        reason = "missing profile_notes for defense traceability"
    if not has_road_plane_polygon_pixel or not has_road_plane_polygon_world:
        status = "needs_manual_refinement"
        reason = "missing road_plane_polygon_pixel/world ground-plane bounds"
    calibration_consistent = (
        qa_row.get("calibration_source") == analysis_calibration.get("source")
        and qa_row.get("calibration_trusted") == analysis_calibration.get("trusted")
    )
    if not calibration_consistent:
        status = "pipeline_mismatch"
        reason = (
            "QA calibration source/trust does not match real analysis output: "
            f"qa={qa_row.get('calibration_source')}/{qa_row.get('calibration_trusted')} "
            f"analysis={analysis_calibration.get('source')}/"
            f"{analysis_calibration.get('trusted')}"
        )
    return {
        "clip": clip_name,
        "acceptance_status": status,
        "reason": reason,
        "calibration_source": qa_row.get("calibration_source"),
        "calibration_trusted": qa_row.get("calibration_trusted"),
        "analysis_calibration_source": analysis_calibration.get("source"),
        "analysis_calibration_trusted": analysis_calibration.get("trusted"),
        "calibration_pipeline_consistent": calibration_consistent,
        "declared_trusted": qa_row.get("declared_trusted"),
        "annotation_method": qa_row.get("annotation_method"),
        "evidence_sources": qa_row.get("evidence_sources", []),
        "provenance_trusted": qa_row.get("provenance_trusted"),
        "provenance_issues": qa_row.get("provenance_issues", []),
        "validation_max_error_px": validation_error,
        "world_to_pixel_rmse_px": qa_row.get("world_to_pixel_rmse_px"),
        "point_count": point_count,
        "validation_segment_count": qa_row.get("validation_segment_count"),
        "independent_validation_segment_count": independent_segment_count,
        "has_scale_prior": has_scale_prior,
        "has_profile_notes": has_profile_notes,
        "has_road_plane_polygon_pixel": has_road_plane_polygon_pixel,
        "has_road_plane_polygon_world": has_road_plane_polygon_world,
        "homography_grid_rendered": qa_row.get("grid_rendered"),
        "qa_image": qa_row.get("qa_image"),
        "processed_mp4": str(processed_path),
        "processed_mp4_exists": processed_path.exists(),
        "frame_report_json": str(analysis_dir / f"{clip_stem}.json"),
        "frame_report_json_exists": (analysis_dir / f"{clip_stem}.json").exists(),
        "math_model_card_md": str(math_card_dir / "math_model_card.md"),
        "math_model_card_exists": (math_card_dir / "math_model_card.md").exists(),
        "device": analysis_row.get("device"),
        "effective_processing_fps": analysis_row.get("effective_processing_fps"),
        "frame_count": (analysis_row.get("metadata") or {}).get("frame_count"),
        "active_track_count": len(final_report.get("active_tracks") or []),
        "physics_valid_track_count": sum(
            1 for track in final_report.get("active_tracks", []) if track.get("physics_valid")
        ),
        "total_in": final_report.get("total_in"),
        "total_out": final_report.get("total_out"),
        "scene_priority": scene_priority(final_report),
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Golden Acceptance Table",
        "",
        f"- QA summary: `{payload['qa_summary_path']}`",
        f"- Analysis summary: `{payload['analysis_summary_path']}`",
        f"- Trusted clips: `{payload['trusted_count']}/{payload['clip_count']}`",
        "",
        (
            "| Clip | Status | Source | Trusted | Validation | Grid | "
            "Processed MP4 | Math Card | Reason |"
        ),
        "| --- | --- | --- | --- | ---: | --- | --- | --- | --- |",
    ]
    for row in payload["clips"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    row["clip"],
                    row["acceptance_status"],
                    str(row["calibration_source"]),
                    str(row["calibration_trusted"]),
                    (
                        "N/A"
                        if row["validation_max_error_px"] is None
                        else f"{row['validation_max_error_px']:.2f}px"
                    ),
                    str(row["homography_grid_rendered"]),
                    "yes" if row["processed_mp4_exists"] else "missing",
                    "yes" if row["math_model_card_exists"] else "missing",
                    row["reason"],
                ],
            )
            + " |",
        )
    lines.extend(["", "## Interpretation", ""])
    for row in payload["clips"]:
        lines.append(f"### {row['clip']}")
        lines.append(f"- Scene priority: {row['scene_priority']}")
        lines.append(
            f"- Tracks: {row['active_track_count']} active, "
            f"{row['physics_valid_track_count']} physics-valid"
        )
        lines.append(f"- Flow counts: in={row['total_in']}, out={row['total_out']}")
        lines.append(
            "- Calibration consistency: "
            f"{row['calibration_pipeline_consistent']} "
            f"(analysis={row['analysis_calibration_source']}/"
            f"{row['analysis_calibration_trusted']})",
        )
        lines.append(
            "- Independent validation segments: "
            f"`{row['independent_validation_segment_count']}`",
        )
        lines.append(f"- QA image: `{row['qa_image']}`")
        lines.append(f"- Processed MP4: `{row['processed_mp4']}`")
        lines.append(f"- Math card: `{row['math_model_card_md']}`")
        lines.append("")
    return "\n".join(lines)


def build_acceptance_table(
    qa_summary_path: Path,
    analysis_summary_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    qa_summary = load_json(qa_summary_path)
    analysis_summary = load_json(analysis_summary_path)
    analysis_dir = analysis_summary_path.parent
    analysis_by_clip = {row["clip"]: row for row in analysis_summary["results"]}
    clips = [
        build_row(row, analysis_by_clip[row["clip"]], analysis_dir)
        for row in qa_summary["clips"]
    ]
    payload = {
        "qa_summary_path": str(qa_summary_path),
        "analysis_summary_path": str(analysis_summary_path),
        "clip_count": len(clips),
        "trusted_count": sum(1 for row in clips if row["calibration_trusted"]),
        "clips": clips,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "golden_acceptance_table.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
    )
    (output_dir / "golden_acceptance_table.md").write_text(render_markdown(payload))
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build acceptance table for the four golden calibration clips.",
    )
    parser.add_argument(
        "--qa-summary",
        default="data/outputs/calibration_qa/calibration_qa_summary.json",
    )
    parser.add_argument(
        "--analysis-summary",
        default="data/outputs/golden_acceptance_smoke/summary.json",
    )
    parser.add_argument("--output-dir", default="data/outputs/golden_acceptance_table")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_acceptance_table(
        qa_summary_path=Path(args.qa_summary),
        analysis_summary_path=Path(args.analysis_summary),
        output_dir=Path(args.output_dir),
    )
    print(
        json.dumps(
            {
                "clip_count": payload["clip_count"],
                "trusted_count": payload["trusted_count"],
                "output_dir": args.output_dir,
            },
            ensure_ascii=False,
            indent=2,
        ),
    )


if __name__ == "__main__":
    main()
