from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from application.services.calibration_preset_store import CalibrationPresetStore

from scripts.build_calibration_readiness_report import camera_profile_reuse_target

GOLDEN_CLIPS = [
    "026_complex_signal_day_wide_0115s_30s.mp4",
    "042_pedestrian_crowd_high_view_0270s_30s.mp4",
    "054_dense_city_traffic_4k_elevated_0030s_30s.mp4",
    "058_dense_city_traffic_4k_elevated_0150s_30s.mp4",
]
MIN_RECOMMENDED_CONTROL_POINTS = 8


def load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def safe_dump_yaml(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def _copy_points(points: list[dict[str, Any]]) -> list[dict[str, float]]:
    return [
        {
            "pixel_x": float(point["pixel_x"]),
            "pixel_y": float(point["pixel_y"]),
            "world_x": float(point["world_x"]),
            "world_y": float(point["world_y"]),
        }
        for point in points
    ]


def promote_clip(
    clip_name: str,
    calibration_payload: dict[str, Any],
    camera_payload: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    video_calibrations = calibration_payload.get("video_calibrations", {})
    if clip_name not in video_calibrations:
        return {
            "clip": clip_name,
            "status": "skipped",
            "reason": "missing video calibration preset",
        }, camera_payload
    profile_id = camera_profile_reuse_target(clip_name)
    profiles = camera_payload.setdefault("camera_profiles", {})
    if profile_id not in profiles:
        return {
            "clip": clip_name,
            "status": "skipped",
            "reason": f"missing target camera profile {profile_id}",
            "target_profile": profile_id,
        }, camera_payload

    entry = video_calibrations[clip_name]
    diagnostics = CalibrationPresetStore().validate_entry(entry)
    evidence_issues = []
    if len(entry.get("points", [])) < MIN_RECOMMENDED_CONTROL_POINTS:
        evidence_issues.append("requires at least 8 manual_control_points")
    if not entry.get("scale_prior"):
        evidence_issues.append("missing scale_prior")
    if not entry.get("profile_notes"):
        evidence_issues.append("missing profile_notes")
    if not entry.get("road_plane_polygon_pixel"):
        evidence_issues.append("missing road_plane_polygon_pixel")
    if not entry.get("road_plane_polygon_world"):
        evidence_issues.append("missing road_plane_polygon_world")
    if diagnostics["calibration_trusted"] is not True:
        return {
            "clip": clip_name,
            "status": "blocked",
            "reason": "video calibration is not trusted by validation gate",
            "target_profile": profile_id,
            "validation_max_error_px": diagnostics.get("validation_max_error_px"),
            "declared_calibration_trusted": diagnostics.get(
                "declared_calibration_trusted",
            ),
            "calibration_quality": diagnostics.get("calibration_quality"),
        }, camera_payload
    if evidence_issues:
        return {
            "clip": clip_name,
            "status": "blocked",
            "reason": "; ".join(evidence_issues),
            "target_profile": profile_id,
            "validation_max_error_px": diagnostics.get("validation_max_error_px"),
            "declared_calibration_trusted": diagnostics.get(
                "declared_calibration_trusted",
            ),
            "calibration_quality": diagnostics.get("calibration_quality"),
        }, camera_payload

    next_payload = deepcopy(camera_payload)
    next_profile = next_payload["camera_profiles"][profile_id]
    next_profile["calibration_trusted"] = True
    next_profile["manual_control_points"] = _copy_points(entry["points"])
    next_profile["road_plane_polygon_pixel"] = entry.get("road_plane_polygon_pixel")
    next_profile["road_plane_polygon_world"] = entry.get("road_plane_polygon_world")
    next_profile["validation_segments"] = entry.get("validation_segments", [])
    if entry.get("scale_prior"):
        next_profile["scale_prior"] = entry.get("scale_prior")
        next_profile["scale_prior_used"] = (
            entry.get("scale_prior", {}).get("description")
            or entry.get("scale_prior", {}).get("kind")
        )
    if entry.get("profile_notes"):
        next_profile["profile_notes"] = entry.get("profile_notes")
    for key in (
        "annotation_method",
        "annotation_confidence",
        "evidence_sources",
        "auto_geometry",
        "scale_constraints",
    ):
        if key in entry:
            next_profile[key] = deepcopy(entry[key])
    next_profile["position_rmse_floor_m"] = float(entry["position_rmse_floor_m"])
    next_profile["calibration_scale_uncertainty_pct"] = float(
        entry["calibration_scale_uncertainty_pct"],
    )
    if diagnostics.get("world_width_m", 0) > 0:
        next_profile["world_width_m"] = float(diagnostics["world_width_m"])
    if diagnostics.get("world_length_m", 0) > 0:
        next_profile["world_length_m"] = float(diagnostics["world_length_m"])
    return {
        "clip": clip_name,
        "status": "promoted",
        "target_profile": profile_id,
        "validation_max_error_px": diagnostics.get("validation_max_error_px"),
        "world_to_pixel_rmse_px": diagnostics.get("world_to_pixel_rmse_px"),
        "point_count": len(entry.get("points", [])),
        "validation_segment_count": len(entry.get("validation_segments", [])),
    }, next_payload


def promote_calibrations(
    calibration_presets: Path,
    camera_profiles: Path,
    clips: list[str],
    *,
    write: bool,
) -> dict[str, Any]:
    calibration_payload = load_yaml(calibration_presets)
    camera_payload = load_yaml(camera_profiles)
    next_camera_payload = camera_payload
    results: list[dict[str, Any]] = []
    for clip in clips:
        result, next_camera_payload = promote_clip(
            clip,
            calibration_payload,
            next_camera_payload,
        )
        results.append(result)
    if write and any(result["status"] == "promoted" for result in results):
        safe_dump_yaml(camera_profiles, next_camera_payload)
    return {
        "calibration_presets": str(calibration_presets),
        "camera_profiles": str(camera_profiles),
        "write": write,
        "promoted_count": sum(1 for result in results if result["status"] == "promoted"),
        "blocked_count": sum(1 for result in results if result["status"] == "blocked"),
        "skipped_count": sum(1 for result in results if result["status"] == "skipped"),
        "results": results,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Promote trusted video_manual_preset calibrations into reusable "
            "camera_manual_preset profiles."
        ),
    )
    parser.add_argument("--calibration-presets", default="data/tests/calibration_presets.yaml")
    parser.add_argument("--camera-profiles", default="data/tests/camera_profiles.yaml")
    parser.add_argument("--clips", nargs="*", default=GOLDEN_CLIPS)
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write camera_profiles.yaml. Without this flag the script is a dry run.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = promote_calibrations(
        calibration_presets=Path(args.calibration_presets),
        camera_profiles=Path(args.camera_profiles),
        clips=args.clips,
        write=args.write,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
