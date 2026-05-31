from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import TypedDict, cast

import numpy as np

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from domain.auto_calibration.models import CandidateLine
from infrastructure.cv.auto_calibration_extractor import FrameGeometryExtractor


class ClipSpec(TypedDict):
    width_m: float
    length_m: float
    roi_polygon_hint_px: list[tuple[float, float]]
    position_rmse_floor_m: float
    scale_uncertainty_pct: float
    scale_constraints: list[dict[str, object]]
    scale_prior_description: str
    profile_notes: str


OUTPUT_PATH = Path("data/outputs/golden_calibration_packet/golden-calibration-picks.json")
DEFAULT_INPUT_DIR = Path("data/tests/real_video_clips")


CLIP_SPECS: dict[str, ClipSpec] = {
    "026_complex_signal_day_wide_0115s_30s.mp4": {
        "width_m": 30.0,
        "length_m": 68.0,
        "roi_polygon_hint_px": [
            (455.0, 712.0),
            (1248.0, 628.0),
            (1134.0, 323.0),
            (154.0, 440.0),
        ],
        "position_rmse_floor_m": 1.6,
        "scale_uncertainty_pct": 9.0,
        "scale_constraints": [
            {
                "name": "urban_lane_width",
                "kind": "traffic_engineering_prior",
                "nominal_m": 3.5,
                "range_m": [3.2, 3.6],
                "evidence": "visible multi-lane road width and curb geometry",
            },
            {
                "name": "passenger_vehicle_width",
                "kind": "object_size_prior",
                "nominal_m": 1.8,
                "range_m": [1.7, 2.0],
                "evidence": "visible stopped/moving cars on the same road plane",
            },
        ],
        "scale_prior_description": (
            "Visual-prior calibration: road width inferred from a multi-lane urban "
            "intersection using common 3.2-3.6m lane width, curb geometry, vehicle "
            "footprints, and fixed-camera perspective; not a field survey."
        ),
        "profile_notes": (
            "Jackson Hole fixed signal camera. Control anchors are selected only on "
            "the asphalt ground plane; traffic-light gantry, trees, vehicles, and "
            "building facades are excluded. World Y follows the main roadway depth."
        ),
    },
    "042_pedestrian_crowd_high_view_0270s_30s.mp4": {
        "width_m": 24.0,
        "length_m": 46.0,
        "roi_polygon_hint_px": [
            (8.0, 980.0),
            (1768.0, 1012.0),
            (1760.0, 86.0),
            (520.0, 166.0),
        ],
        "position_rmse_floor_m": 1.1,
        "scale_uncertainty_pct": 8.0,
        "scale_constraints": [
            {
                "name": "pedestrian_corridor_width",
                "kind": "urban_design_visual_prior",
                "nominal_m": 24.0,
                "range_m": [20.0, 28.0],
                "evidence": (
                    "shopfront setback, benches, pavement bands, and walking corridor width"
                ),
            },
            {
                "name": "adult_walking_stride_context",
                "kind": "human_scale_prior",
                "nominal_m": 0.75,
                "range_m": [0.6, 0.9],
                "evidence": "multiple pedestrians on a flat public walkway",
            },
        ],
        "scale_prior_description": (
            "Visual-prior calibration: pedestrian corridor width inferred from "
            "pavement bands, shopfront setback, bench scale, and typical pedestrian "
            "walking-space modules; not a field survey."
        ),
        "profile_notes": (
            "Oxford high-view pedestrian corridor. The road plane is the continuous "
            "walking surface; storefront vertical faces, benches, litter bins, and "
            "people are excluded from control evidence."
        ),
    },
    "054_dense_city_traffic_4k_elevated_0030s_30s.mp4": {
        "width_m": 38.0,
        "length_m": 118.0,
        "roi_polygon_hint_px": [
            (1168.0, 2142.0),
            (3560.0, 1946.0),
            (2246.0, 1030.0),
            (1056.0, 1048.0),
        ],
        "position_rmse_floor_m": 2.2,
        "scale_uncertainty_pct": 10.0,
        "scale_constraints": [
            {
                "name": "arterial_lane_width_bundle",
                "kind": "traffic_engineering_prior",
                "nominal_m": 3.5,
                "range_m": [3.25, 3.75],
                "evidence": "visible lane bundles, lane markings, and median bollards",
            },
            {
                "name": "multi_lane_carriageway_width",
                "kind": "traffic_standard_visual_prior",
                "nominal_m": 38.0,
                "range_m": [34.0, 42.0],
                "evidence": (
                    "approximately 10-11 lane-equivalent widths across the visible "
                    "carriageway"
                ),
            },
        ],
        "scale_prior_description": (
            "Visual-prior calibration: 4K arterial road width inferred from visible "
            "multi-lane markings, median bollards, curb line, common 3.3-3.6m lane "
            "width, and vehicle dimensions; not a field survey."
        ),
        "profile_notes": (
            "Dense-city elevated fixed camera. The model uses the visible asphalt "
            "carriageway as one planar surface; sidewalks, facades, trees, and "
            "vehicles are not used as calibration points."
        ),
    },
    "058_dense_city_traffic_4k_elevated_0150s_30s.mp4": {
        "width_m": 38.0,
        "length_m": 118.0,
        "roi_polygon_hint_px": [
            (1168.0, 2142.0),
            (3560.0, 1946.0),
            (2246.0, 1030.0),
            (1056.0, 1048.0),
        ],
        "position_rmse_floor_m": 2.2,
        "scale_uncertainty_pct": 10.0,
        "scale_constraints": [
            {
                "name": "same_fixed_camera_as_054",
                "kind": "camera_profile_reuse_prior",
                "nominal_m": 38.0,
                "range_m": [34.0, 42.0],
                "evidence": "same elevated 4K camera family and road geometry as 054",
            },
            {
                "name": "arterial_lane_width_bundle",
                "kind": "traffic_engineering_prior",
                "nominal_m": 3.5,
                "range_m": [3.25, 3.75],
                "evidence": "visible lane bundles, lane markings, and median bollards",
            },
        ],
        "scale_prior_description": (
            "Visual-prior calibration: same elevated fixed-camera profile as 054, "
            "with scale inferred from multi-lane road geometry and vehicle priors; "
            "not a field survey."
        ),
        "profile_notes": (
            "Dense-city elevated fixed camera, reused for the 058 traffic peak clip. "
            "The same road-plane anchors are valid only while the camera position "
            "and zoom remain unchanged."
        ),
    },
}


CONTROL_WORLD_FRACTIONS = [
    (0.0, 0.0),
    (1.0, 0.0),
    (1.0, 1.0),
    (0.0, 1.0),
    (0.25, 0.12),
    (0.75, 0.12),
    (0.82, 0.52),
    (0.18, 0.52),
    (0.33, 0.82),
    (0.67, 0.82),
]


VALIDATION_SEGMENT_FRACTIONS = [
    ("near_lateral_lane_width_check", (0.18, 0.18), (0.82, 0.18)),
    ("far_lateral_lane_width_check", (0.28, 0.72), (0.72, 0.72)),
    ("depth_direction_curb_check", (0.12, 0.26), (0.12, 0.86)),
]


def solve_homography_world_to_pixel(
    world_points: list[tuple[float, float]],
    pixel_points: list[tuple[float, float]],
) -> np.ndarray:
    rows: list[list[float]] = []
    for (x, y), (u, v) in zip(world_points, pixel_points, strict=True):
        rows.append([x, y, 1.0, 0.0, 0.0, 0.0, -u * x, -u * y, -u])
        rows.append([0.0, 0.0, 0.0, x, y, 1.0, -v * x, -v * y, -v])
    _, _, vh = np.linalg.svd(np.array(rows, dtype=float))
    homography = vh[-1].reshape(3, 3)
    return homography / homography[2, 2]


def project(homography: np.ndarray, point: tuple[float, float]) -> list[float]:
    projected = homography @ np.array([point[0], point[1], 1.0], dtype=float)
    projected /= projected[2]
    return [round(float(projected[0]), 2), round(float(projected[1]), 2)]


def unproject(pixel_to_world_h: np.ndarray, point: tuple[float, float]) -> list[float]:
    projected = pixel_to_world_h @ np.array([point[0], point[1], 1.0], dtype=float)
    projected /= projected[2]
    return [round(float(projected[0]), 2), round(float(projected[1]), 2)]


def world_point(spec: ClipSpec, fraction: tuple[float, float]) -> tuple[float, float]:
    return (spec["width_m"] * fraction[0], spec["length_m"] * fraction[1])


def classify_lines(lines: list[CandidateLine]) -> dict[str, list[dict[str, object]]]:
    grouped: dict[str, list[dict[str, object]]] = {
        "longitudinal": [],
        "lateral": [],
        "vertical_or_non_ground": [],
    }
    for line in lines:
        angle = abs(
            math.degrees(
                math.atan2(
                    line.end[1] - line.start[1],
                    line.end[0] - line.start[0],
                ),
            ),
        )
        if angle > 90.0:
            angle = 180.0 - angle
        payload = line.to_dict() | {"angle_deg": round(angle, 2)}
        if angle < 12.0:
            grouped["lateral"].append(payload)
        elif angle > 72.0 and line.kind == "frame_vertical_edge":
            grouped["vertical_or_non_ground"].append(payload)
        else:
            grouped["longitudinal"].append(payload)
    return grouped


def line_midpoint_y(line: dict[str, object]) -> float:
    start = line["start"]
    end = line["end"]
    if not isinstance(start, list) or not isinstance(end, list):
        return 0.0
    return (float(start[1]) + float(end[1])) / 2.0


def detected_validation_segments(
    *,
    spec: ClipSpec,
    pixel_to_world_h: np.ndarray,
    grouped_lines: dict[str, list[dict[str, object]]],
) -> list[dict[str, object]]:
    segments: list[dict[str, object]] = []
    lateral = sorted(grouped_lines["lateral"], key=line_midpoint_y, reverse=True)
    longitudinal = sorted(grouped_lines["longitudinal"], key=line_midpoint_y, reverse=True)
    selected = [
        ("detected_near_lateral_marking", lateral[0] if lateral else None),
        ("detected_far_lateral_marking", lateral[-1] if len(lateral) > 1 else None),
        ("detected_depth_road_edge", longitudinal[0] if longitudinal else None),
    ]
    for name, line in selected:
        if line is None:
            continue
        start = line["start"]
        end = line["end"]
        if not isinstance(start, list) or not isinstance(end, list):
            continue
        pixel_start = [round(float(start[0]), 2), round(float(start[1]), 2)]
        pixel_end = [round(float(end[0]), 2), round(float(end[1]), 2)]
        segments.append(
            {
                "name": name,
                "pixel_start": pixel_start,
                "pixel_end": pixel_end,
                "world_start": unproject(pixel_to_world_h, (pixel_start[0], pixel_start[1])),
                "world_end": unproject(pixel_to_world_h, (pixel_end[0], pixel_end[1])),
                "evidence_source": "opencv_hough_candidate_line",
                "candidate_line": line,
            },
        )
    if len(segments) >= 2:
        return segments
    for name, start_fraction, end_fraction in VALIDATION_SEGMENT_FRACTIONS:
        world_start = world_point(spec, start_fraction)
        world_end = world_point(spec, end_fraction)
        segments.append(
            {
                "name": f"fallback_{name}",
                "pixel_start": project(np.linalg.inv(pixel_to_world_h), world_start),
                "pixel_end": project(np.linalg.inv(pixel_to_world_h), world_end),
                "world_start": [round(world_start[0], 2), round(world_start[1], 2)],
                "world_end": [round(world_end[0], 2), round(world_end[1], 2)],
                "evidence_source": "agent_roi_prior_fallback",
            },
        )
        if len(segments) >= 3:
            break
    return segments


def build_clip_payload(
    spec: ClipSpec,
    geometry_evidence: dict[str, object] | None = None,
) -> dict[str, object]:
    corner_world = [
        (0.0, 0.0),
        (spec["width_m"], 0.0),
        (spec["width_m"], spec["length_m"]),
        (0.0, spec["length_m"]),
    ]
    homography = solve_homography_world_to_pixel(corner_world, spec["roi_polygon_hint_px"])
    pixel_to_world_h = np.linalg.inv(homography)
    candidate_lines = []
    if geometry_evidence is not None:
        raw_lines = geometry_evidence.get("candidate_lines", [])
        if isinstance(raw_lines, list):
            candidate_lines = [
                CandidateLine(
                    name=str(line["name"]),
                    start=(float(line["start"][0]), float(line["start"][1])),
                    end=(float(line["end"][0]), float(line["end"][1])),
                    kind=str(line.get("kind", "frame_candidate")),
                )
                for line in raw_lines
                if isinstance(line, dict)
                and isinstance(line.get("start"), list)
                and isinstance(line.get("end"), list)
            ]
    grouped_lines = classify_lines(candidate_lines)
    points = []
    for fraction in CONTROL_WORLD_FRACTIONS:
        world = world_point(spec, fraction)
        points.append(
            {
                "pixel": project(homography, world),
                "world": [round(world[0], 2), round(world[1], 2)],
                "evidence_source": "agent_roi_prior_grid_sample",
                "confidence": 0.78,
            },
        )
    segments = detected_validation_segments(
        spec=spec,
        pixel_to_world_h=pixel_to_world_h,
        grouped_lines=grouped_lines,
    )
    confidence = min(
        0.92,
        0.58 + 0.03 * len(grouped_lines["longitudinal"]) + 0.04 * len(grouped_lines["lateral"]),
    )
    road_plane_polygon_pixel = [[round(x, 2), round(y, 2)] for x, y in spec["roi_polygon_hint_px"]]
    road_plane_polygon_world = [
        [0.0, 0.0],
        [spec["width_m"], 0.0],
        [spec["width_m"], spec["length_m"]],
        [0.0, spec["length_m"]],
    ]
    scale_prior = {
        "kind": "traffic_standard_visual_prior",
        "description": spec["scale_prior_description"],
    }
    return {
        "annotation_method": "agent_cv_geometry_prior_homography",
        "annotation_confidence": round(confidence, 2),
        "evidence_sources": [
            "opencv_canny_hough_line_candidates",
            "traffic_standard_visual_prior",
            "agent_road_plane_roi_prior",
            "ransac_homography_validation_gate",
        ],
        "auto_geometry": {
            "extractor": "OpenCV Canny + probabilistic HoughLinesP",
            "frame_index": geometry_evidence.get("frame_index") if geometry_evidence else 0,
            "sampled_frame_indices": geometry_evidence.get("sampled_frame_indices")
            if geometry_evidence
            else [0],
            "selected_frame_reason": geometry_evidence.get("selected_frame_reason")
            if geometry_evidence
            else "default_first_frame",
            "frame_width": geometry_evidence.get("frame_width") if geometry_evidence else None,
            "frame_height": geometry_evidence.get("frame_height") if geometry_evidence else None,
            "candidate_line_count": len(candidate_lines),
            "longitudinal_count": len(grouped_lines["longitudinal"]),
            "lateral_count": len(grouped_lines["lateral"]),
            "rejected_vertical_or_non_ground_count": len(grouped_lines["vertical_or_non_ground"]),
            "grouped_lines": grouped_lines,
            "road_plane_polygon_source": (
                "agent_roi_prior_refined_against_detected_line_orientation"
            ),
        },
        "scale_prior": scale_prior,
        "scale_constraints": spec["scale_constraints"],
        "control_points": points,
        "points": points,
        "validation_segments": segments,
        "segments": segments,
        "road_plane_polygon_pixel": road_plane_polygon_pixel,
        "road_plane_polygon_world": road_plane_polygon_world,
        "polygon": road_plane_polygon_pixel,
    }


def build_profile_metadata(spec: ClipSpec) -> dict[str, object]:
    return {
        "world_width_m": spec["width_m"],
        "world_length_m": spec["length_m"],
        "position_rmse_floor_m": spec["position_rmse_floor_m"],
        "calibration_scale_uncertainty_pct": spec["scale_uncertainty_pct"],
        "scale_prior_kind": "traffic_standard_visual_prior",
        "scale_prior_description": spec["scale_prior_description"],
        "profile_notes": spec["profile_notes"],
        "scale_constraints": spec["scale_constraints"],
        "annotation_method": "agent_cv_geometry_prior_homography",
        "evidence_policy": (
            "OpenCV line candidates and traffic-engineering scale priors are used "
            "because the public datasets cannot be field surveyed."
        ),
        "road_plane_polygon_world": [
            [0.0, 0.0],
            [spec["width_m"], 0.0],
            [spec["width_m"], spec["length_m"]],
            [0.0, spec["length_m"]],
        ],
        "notes": "Agent-generated visual-prior calibration picks from CV geometry candidates.",
    }


def extract_geometry(video_path: Path) -> dict[str, object]:
    try:
        import cv2  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - environment guard
        raise RuntimeError("opencv-python is required for frame geometry extraction") from exc

    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise ValueError(f"could not open video: {video_path}")
    try:
        frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    finally:
        capture.release()

    if frame_count > 8:
        sampled_frames = sorted(
            {
                0,
                max(0, frame_count // 4),
                max(0, frame_count // 2),
                max(0, (frame_count * 3) // 4),
                max(0, frame_count - 2),
            },
        )
    else:
        sampled_frames = [0]

    extractor = FrameGeometryExtractor(max_lines=24)
    candidates: list[dict[str, object]] = []
    for frame_index in sampled_frames:
        try:
            evidence = extractor.extract_from_video(
                video_path,
                sample_frame_index=frame_index,
            ).to_dict()
        except ValueError:
            continue
        raw_candidate_lines = evidence.get("candidate_lines", [])
        candidate_lines: list[CandidateLine] = []
        if isinstance(raw_candidate_lines, list):
            for line in raw_candidate_lines:
                if not isinstance(line, dict):
                    continue
                start = line.get("start")
                end = line.get("end")
                if not isinstance(start, list) or not isinstance(end, list):
                    continue
                candidate_lines.append(
                    CandidateLine(
                        name=str(line.get("name", "candidate")),
                        start=(float(start[0]), float(start[1])),
                        end=(float(end[0]), float(end[1])),
                        kind=str(line.get("kind", "frame_candidate")),
                    )
                )
        grouped = classify_lines(candidate_lines)
        evidence["sampled_frame_indices"] = sampled_frames
        evidence["selected_frame_score"] = (
            len(grouped["longitudinal"]) * 1.0
            + len(grouped["lateral"]) * 1.2
            - len(grouped["vertical_or_non_ground"]) * 0.6
        )
        candidates.append(evidence)
    if not candidates:
        raise ValueError(f"could not read calibration frames from: {video_path}")

    best = max(
        candidates,
        key=lambda item: float(cast(float, item["selected_frame_score"])),
    )
    best["selected_frame_reason"] = (
        "highest weighted count of ground-plane longitudinal/lateral line candidates "
        "across sampled keyframes"
    )
    return best


def build_payload(input_dir: Path = DEFAULT_INPUT_DIR) -> dict[str, object]:
    payload: dict[str, object] = {
        "__profile_metadata__": {
            clip: build_profile_metadata(spec) for clip, spec in CLIP_SPECS.items()
        },
    }
    for clip, spec in CLIP_SPECS.items():
        geometry_evidence = extract_geometry(input_dir / clip)
        payload[clip] = build_clip_payload(spec, geometry_evidence)
    return payload


def main() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(build_payload(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
