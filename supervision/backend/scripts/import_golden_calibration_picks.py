from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from application.services.calibration_preset_store import CalibrationPresetStore


def load_payload(path: Path) -> dict[str, Any]:
    if path.suffix.lower() in {".yaml", ".yml"}:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    else:
        payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _pair(value: Any, field_name: str) -> list[float]:
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError(f"{field_name} must be a [x, y] pair")
    return [float(value[0]), float(value[1])]


def _world_polygon(width_m: float, length_m: float) -> list[list[float]]:
    if width_m <= 0 or length_m <= 0:
        raise ValueError("world width/length must be positive")
    return [[0.0, 0.0], [width_m, 0.0], [width_m, length_m], [0.0, length_m]]


def _required_text(value: Any, field_name: str) -> str:
    text = str(value or "").strip()
    if not text or "TODO" in text.upper() or "REPLACE" in text.upper():
        raise ValueError(f"{field_name} must be a real non-placeholder value")
    return text


def _points(raw_points: Any) -> list[dict[str, float]]:
    if not isinstance(raw_points, list):
        raise ValueError("points must be a list")
    points = []
    for index, point in enumerate(raw_points, start=1):
        if not isinstance(point, dict):
            raise ValueError(f"point {index} must be an object")
        pixel = _pair(point.get("pixel"), f"point {index}.pixel")
        world = _pair(point.get("world"), f"point {index}.world")
        points.append(
            {
                "pixel_x": pixel[0],
                "pixel_y": pixel[1],
                "world_x": world[0],
                "world_y": world[1],
            },
        )
    return points


def _string_list(raw_values: Any) -> list[str]:
    if not isinstance(raw_values, list):
        return []
    return [str(value) for value in raw_values if str(value).strip()]


def _segments(raw_segments: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_segments, list):
        return []
    segments = []
    for index, segment in enumerate(raw_segments, start=1):
        if not isinstance(segment, dict):
            raise ValueError(f"segment {index} must be an object")
        segments.append(
            {
                "name": str(segment.get("name") or f"independent_segment_{index}"),
                "pixel_start": _pair(segment.get("pixel_start"), f"segment {index}.pixel_start"),
                "pixel_end": _pair(segment.get("pixel_end"), f"segment {index}.pixel_end"),
                "world_start": _pair(segment.get("world_start"), f"segment {index}.world_start"),
                "world_end": _pair(segment.get("world_end"), f"segment {index}.world_end"),
            },
        )
    return segments


def _pixel_polygon(raw_polygon: Any) -> list[list[float]] | None:
    if raw_polygon is None:
        return None
    if not isinstance(raw_polygon, list):
        raise ValueError("polygon must be a list of [x, y] pairs")
    polygon = [_pair(point, "polygon point") for point in raw_polygon]
    return polygon if len(polygon) >= 3 else None


def metadata_from_picks(picks: dict[str, Any]) -> dict[str, Any]:
    metadata = picks.get("__profile_metadata__")
    return metadata if isinstance(metadata, dict) else {}


def calibration_pick_keys(picks: dict[str, Any]) -> list[str]:
    return sorted(key for key in picks if not key.startswith("__"))


def _require_trusted_evidence(
    clip_name: str,
    points: list[dict[str, float]],
    segments: list[dict[str, Any]],
    road_plane_polygon_pixel: list[list[float]] | None,
) -> None:
    issues: list[str] = []
    if len(points) < 8:
        issues.append(f"requires at least 8 manual control points; found {len(points)}")
    if len(segments) < 2:
        issues.append(
            f"requires at least 2 independent validation segment candidates; found {len(segments)}",
        )
    if road_plane_polygon_pixel is None:
        issues.append("requires road_plane_polygon_pixel with at least 3 points")
    if issues:
        joined = "; ".join(issues)
        raise ValueError(f"{clip_name} cannot be imported as trusted: {joined}")


def build_entry(
    clip_name: str,
    pick: dict[str, Any],
    profile: dict[str, Any],
    *,
    trusted: bool,
) -> dict[str, Any]:
    width_m = float(profile["world_width_m"])
    length_m = float(profile["world_length_m"])
    points = _points(pick.get("control_points") or pick.get("points", []))
    validation_segments = _segments(
        pick.get("validation_segments") or pick.get("segments", []),
    )
    road_plane_polygon_pixel = _pixel_polygon(
        pick.get("road_plane_polygon_pixel") or pick.get("polygon"),
    )
    if trusted:
        _require_trusted_evidence(
            clip_name,
            points,
            validation_segments,
            road_plane_polygon_pixel,
        )
    return {
        "notes": str(profile.get("notes") or f"Manual picks imported for {clip_name}."),
        "position_rmse_floor_m": float(profile.get("position_rmse_floor_m", 1.0)),
        "calibration_scale_uncertainty_pct": float(
            profile.get("calibration_scale_uncertainty_pct", 5.0),
        ),
        "calibration_trusted": trusted,
        "annotation_method": str(
            pick.get("annotation_method")
            or profile.get("annotation_method")
            or "manual_calibration_picker",
        ),
        "annotation_confidence": float(pick.get("annotation_confidence", 0.0) or 0.0),
        "evidence_sources": _string_list(
            pick.get("evidence_sources") or profile.get("evidence_sources"),
        ),
        "auto_geometry": pick.get("auto_geometry")
        if isinstance(pick.get("auto_geometry"), dict)
        else None,
        "scale_constraints": (
            pick.get("scale_constraints")
            if isinstance(pick.get("scale_constraints"), list)
            else profile.get("scale_constraints")
            if isinstance(profile.get("scale_constraints"), list)
            else []
        ),
        "scale_prior": {
            "kind": str(
                (pick.get("scale_prior") or {}).get("kind")
                if isinstance(pick.get("scale_prior"), dict)
                else profile.get("scale_prior_kind", "traffic_standard_or_survey"),
            ),
            "description": _required_text(
                (pick.get("scale_prior") or {}).get("description")
                if isinstance(pick.get("scale_prior"), dict)
                else profile.get("scale_prior_description"),
                "scale_prior_description",
            ),
        },
        "profile_notes": _required_text(profile.get("profile_notes"), "profile_notes"),
        "road_plane_polygon_pixel": road_plane_polygon_pixel,
        "road_plane_polygon_world": pick.get("road_plane_polygon_world")
        or profile.get("road_plane_polygon_world")
        or _world_polygon(width_m, length_m),
        "validation_segments": validation_segments,
        "points": points,
    }


def import_picks(
    picks_path: Path,
    profile_metadata_path: Path | None,
    calibration_presets: Path,
    *,
    clips: list[str] | None = None,
    trusted: bool = False,
) -> dict[str, Any]:
    picks = load_payload(picks_path)
    profiles = (
        load_payload(profile_metadata_path)
        if profile_metadata_path is not None
        else metadata_from_picks(picks)
    )
    requested_clips = clips or calibration_pick_keys(picks)
    store = CalibrationPresetStore(calibration_presets)
    results = []
    for clip in requested_clips:
        if clip not in picks:
            raise ValueError(f"missing picks for clip: {clip}")
        if clip not in profiles:
            raise ValueError(f"missing profile metadata for clip: {clip}")
        entry = build_entry(clip, picks[clip], profiles[clip], trusted=trusted)
        saved = store.upsert_entry(clip, entry)
        diagnostics = saved["diagnostics"]
        results.append(
            {
                "clip": clip,
                "point_count": len(entry["points"]),
                "validation_segment_count": len(entry["validation_segments"]),
                "calibration_trusted": diagnostics["calibration_trusted"],
                "validation_max_error_px": diagnostics["validation_max_error_px"],
                "world_to_pixel_rmse_px": diagnostics["world_to_pixel_rmse_px"],
                "independent_validation_segment_count": diagnostics[
                    "independent_validation_segment_count"
                ],
            },
        )
    return {
        "picks_path": str(picks_path),
        "profile_metadata_path": str(profile_metadata_path)
        if profile_metadata_path is not None
        else "embedded:__profile_metadata__",
        "calibration_presets": str(calibration_presets),
        "trusted_requested": trusted,
        "imported_count": len(results),
        "trusted_count": sum(1 for row in results if row["calibration_trusted"]),
        "results": results,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import golden calibration picker JSON into calibration_presets.yaml.",
    )
    parser.add_argument("--picks", required=True, help="JSON exported by golden picker.")
    parser.add_argument(
        "--profile-metadata",
        default=None,
        help=(
            "YAML/JSON with per-clip world dimensions, scale prior, and notes. "
            "If omitted, reads __profile_metadata__ from the picker JSON."
        ),
    )
    parser.add_argument("--calibration-presets", default="data/tests/calibration_presets.yaml")
    parser.add_argument("--clips", nargs="*", default=None)
    parser.add_argument(
        "--trusted",
        action="store_true",
        help="Declare imported entries trusted; validation gates may still persist false.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = import_picks(
        picks_path=Path(args.picks),
        profile_metadata_path=Path(args.profile_metadata)
        if args.profile_metadata
        else None,
        calibration_presets=Path(args.calibration_presets),
        clips=args.clips,
        trusted=args.trusted,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
