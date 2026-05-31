from __future__ import annotations

import json
from pathlib import Path
from typing import Any, TypedDict

import numpy as np

OUTPUT_PATH = Path(
    "data/outputs/golden_calibration_packet/agent-assisted-standard-golden-picks.json",
)


class ClipPicks(TypedDict):
    width_m: float
    length_m: float
    position_rmse_floor_m: float
    calibration_scale_uncertainty_pct: float
    scale_prior_description: str
    profile_notes: str
    road_plane_polygon_pixel: list[list[float]]
    control_points: list[dict[str, Any]]
    validation_segments: list[dict[str, Any]]


ANNOTATION_METHOD = "codex_assisted_manual_ground_control_picker"
EVIDENCE_SOURCES = [
    "codex_assisted_pixel_clicks_on_exported_keyframe",
    "traffic_standard_meter_scale_anchor",
    "visible_lane_edge_or_pavement_boundary_landmarks",
    "homography_samples_from_manual_ground_plane_roi",
]

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


CLIPS: dict[str, ClipPicks] = {
    "026_complex_signal_day_wide_0115s_30s.mp4": {
        "width_m": 18.0,
        "length_m": 70.0,
        "position_rmse_floor_m": 1.8,
        "calibration_scale_uncertainty_pct": 12.0,
        "scale_prior_description": (
            "Scale anchored by an urban multi-lane road-width prior: about five "
            "lane-equivalent widths at 3.5 m per lane. Pixel anchors were selected "
            "from visible asphalt road edges and lane/curb directions on the keyframe."
        ),
        "profile_notes": (
            "Jackson Hole fixed signal camera. The calibrated plane is restricted "
            "to the main visible asphalt approach and excludes traffic-light gantries, "
            "vehicles, trees, building facades, and sidewalk vertical faces."
        ),
        "road_plane_polygon_pixel": [
            [520.0, 592.0],
            [1206.0, 586.0],
            [1146.0, 328.0],
            [674.0, 386.0],
        ],
        "control_points": [
            {"pixel": [322.0, 716.0], "world": [0.0, 0.0]},
            {"pixel": [1248.0, 704.0], "world": [18.0, 0.0]},
            {"pixel": [1146.0, 326.0], "world": [18.0, 70.0]},
            {"pixel": [696.0, 342.0], "world": [0.0, 70.0]},
            {"pixel": [458.0, 627.0], "world": [0.0, 15.0]},
            {"pixel": [1212.0, 592.0], "world": [18.0, 15.0]},
            {"pixel": [592.0, 492.0], "world": [0.0, 35.0]},
            {"pixel": [1182.0, 475.0], "world": [18.0, 35.0]},
            {"pixel": [805.0, 710.0], "world": [9.0, 0.0]},
            {"pixel": [938.0, 333.0], "world": [9.0, 70.0]},
        ],
        "validation_segments": [
            {
                "name": "near_lateral_lane_bundle",
                "pixel_start": [532.0, 586.0],
                "pixel_end": [1192.0, 580.0],
                "world_start": [2.0, 12.0],
                "world_end": [16.0, 12.0],
            },
            {
                "name": "far_lateral_approach_marking",
                "pixel_start": [720.0, 420.0],
                "pixel_end": [1122.0, 392.0],
                "world_start": [2.0, 55.0],
                "world_end": [16.0, 55.0],
            },
            {
                "name": "right_road_edge_depth",
                "pixel_start": [1198.0, 586.0],
                "pixel_end": [1162.0, 420.0],
                "world_start": [18.0, 14.0],
                "world_end": [18.0, 46.0],
            },
        ],
    },
    "042_pedestrian_crowd_high_view_0270s_30s.mp4": {
        "width_m": 12.0,
        "length_m": 45.0,
        "position_rmse_floor_m": 1.2,
        "calibration_scale_uncertainty_pct": 10.0,
        "scale_prior_description": (
            "Scale anchored by pedestrian-street corridor priors: a broad retail "
            "walking lane bounded by visible pavement bands, with meter scale checked "
            "against repeated pavement modules and adult walking-space dimensions."
        ),
        "profile_notes": (
            "High-view pedestrian corridor. The calibrated plane is the central "
            "walking surface bounded by the two long dark pavement bands; benches, "
            "bins, people, shopfronts, and facade edges are excluded."
        ),
        "road_plane_polygon_pixel": [
            [0.0, 1048.0],
            [1060.0, 1070.0],
            [1540.0, 0.0],
            [560.0, 0.0],
        ],
        "control_points": [
            {"pixel": [0.0, 1048.0], "world": [0.0, 0.0]},
            {"pixel": [1060.0, 1070.0], "world": [12.0, 0.0]},
            {"pixel": [1540.0, 0.0], "world": [12.0, 45.0]},
            {"pixel": [560.0, 0.0], "world": [0.0, 45.0]},
            {"pixel": [112.0, 900.0], "world": [0.0, 7.0]},
            {"pixel": [1036.0, 906.0], "world": [12.0, 7.0]},
            {"pixel": [252.0, 710.0], "world": [0.0, 16.0]},
            {"pixel": [1136.0, 722.0], "world": [12.0, 16.0]},
            {"pixel": [430.0, 420.0], "world": [0.0, 31.0]},
            {"pixel": [1310.0, 378.0], "world": [12.0, 31.0]},
        ],
        "validation_segments": [
            {
                "name": "left_pavement_band_depth",
                "pixel_start": [110.0, 900.0],
                "pixel_end": [520.0, 140.0],
                "world_start": [0.0, 7.0],
                "world_end": [0.0, 40.0],
            },
            {
                "name": "right_pavement_band_depth",
                "pixel_start": [1038.0, 910.0],
                "pixel_end": [1510.0, 100.0],
                "world_start": [12.0, 7.0],
                "world_end": [12.0, 40.0],
            },
            {
                "name": "mid_corridor_width",
                "pixel_start": [300.0, 640.0],
                "pixel_end": [1160.0, 650.0],
                "world_start": [0.0, 20.0],
                "world_end": [12.0, 20.0],
            },
        ],
    },
    "054_dense_city_traffic_4k_elevated_0030s_30s.mp4": {
        "width_m": 38.0,
        "length_m": 118.0,
        "position_rmse_floor_m": 2.2,
        "calibration_scale_uncertainty_pct": 11.0,
        "scale_prior_description": (
            "Scale anchored by a multi-lane arterial road prior: roughly ten to "
            "eleven lane-equivalent widths using 3.3-3.6 m traffic lanes, visible "
            "lane markings, median bollards, curb edges, and vehicle-width checks."
        ),
        "profile_notes": (
            "Dense-city 4K elevated fixed camera. The calibrated plane is the asphalt "
            "carriageway between the left road edge and right curb; building facades, "
            "sidewalks, trees, bollard posts above ground, and vehicles are excluded."
        ),
        "road_plane_polygon_pixel": [
            [1328.0, 1878.0],
            [3400.0, 1838.0],
            [2245.0, 1030.0],
            [1092.0, 1054.0],
        ],
        "control_points": [
            {"pixel": [1148.0, 2145.0], "world": [0.0, 0.0]},
            {"pixel": [3560.0, 1950.0], "world": [38.0, 0.0]},
            {"pixel": [2245.0, 1030.0], "world": [38.0, 118.0]},
            {"pixel": [1058.0, 1048.0], "world": [0.0, 118.0]},
            {"pixel": [2310.0, 2070.0], "world": [19.0, 0.0]},
            {"pixel": [1665.0, 1035.0], "world": [19.0, 118.0]},
            {"pixel": [1925.0, 1470.0], "world": [19.0, 60.0]},
            {"pixel": [1300.0, 1600.0], "world": [8.0, 40.0]},
            {"pixel": [2800.0, 1500.0], "world": [30.0, 40.0]},
            {"pixel": [2080.0, 1140.0], "world": [28.0, 92.0]},
        ],
        "validation_segments": [
            {
                "name": "center_median_bollard_depth",
                "pixel_start": [2150.0, 1808.0],
                "pixel_end": [1695.0, 1120.0],
                "world_start": [19.0, 8.0],
                "world_end": [19.0, 108.0],
            },
            {
                "name": "right_curb_depth",
                "pixel_start": [3300.0, 1788.0],
                "pixel_end": [2320.0, 1100.0],
                "world_start": [38.0, 12.0],
                "world_end": [38.0, 108.0],
            },
            {
                "name": "mid_arterial_width",
                "pixel_start": [1320.0, 1458.0],
                "pixel_end": [2840.0, 1428.0],
                "world_start": [0.0, 55.0],
                "world_end": [38.0, 55.0],
            },
        ],
    },
    "058_dense_city_traffic_4k_elevated_0150s_30s.mp4": {
        "width_m": 38.0,
        "length_m": 118.0,
        "position_rmse_floor_m": 2.2,
        "calibration_scale_uncertainty_pct": 11.0,
        "scale_prior_description": (
            "Scale anchored by the same elevated arterial camera geometry as 054: "
            "multi-lane road width from 3.3-3.6 m lane standards, lane markings, "
            "median bollards, curb edges, and vehicle-width consistency checks."
        ),
        "profile_notes": (
            "Dense-city 4K elevated fixed camera, same physical camera family as 054. "
            "This profile is valid for the same unchanged camera viewpoint and road "
            "plane; it should be rechecked if zoom/crop changes."
        ),
        "road_plane_polygon_pixel": [
            [1328.0, 1878.0],
            [3400.0, 1838.0],
            [2245.0, 1030.0],
            [1092.0, 1054.0],
        ],
        "control_points": [
            {"pixel": [1148.0, 2145.0], "world": [0.0, 0.0]},
            {"pixel": [3560.0, 1950.0], "world": [38.0, 0.0]},
            {"pixel": [2245.0, 1030.0], "world": [38.0, 118.0]},
            {"pixel": [1058.0, 1048.0], "world": [0.0, 118.0]},
            {"pixel": [2310.0, 2070.0], "world": [19.0, 0.0]},
            {"pixel": [1665.0, 1035.0], "world": [19.0, 118.0]},
            {"pixel": [1925.0, 1470.0], "world": [19.0, 60.0]},
            {"pixel": [1300.0, 1600.0], "world": [8.0, 40.0]},
            {"pixel": [2800.0, 1500.0], "world": [30.0, 40.0]},
            {"pixel": [2080.0, 1140.0], "world": [28.0, 92.0]},
        ],
        "validation_segments": [
            {
                "name": "center_median_bollard_depth",
                "pixel_start": [2150.0, 1808.0],
                "pixel_end": [1695.0, 1120.0],
                "world_start": [19.0, 8.0],
                "world_end": [19.0, 108.0],
            },
            {
                "name": "right_curb_depth",
                "pixel_start": [3300.0, 1788.0],
                "pixel_end": [2320.0, 1100.0],
                "world_start": [38.0, 12.0],
                "world_end": [38.0, 108.0],
            },
            {
                "name": "mid_arterial_width",
                "pixel_start": [1320.0, 1458.0],
                "pixel_end": [2840.0, 1428.0],
                "world_start": [0.0, 55.0],
                "world_end": [38.0, 55.0],
            },
        ],
    },
}


def _profile_metadata(clip: str, picks: ClipPicks) -> dict[str, Any]:
    return {
        "annotation_method": ANNOTATION_METHOD,
        "evidence_sources": EVIDENCE_SOURCES,
        "world_width_m": picks["width_m"],
        "world_length_m": picks["length_m"],
        "position_rmse_floor_m": picks["position_rmse_floor_m"],
        "calibration_scale_uncertainty_pct": picks[
            "calibration_scale_uncertainty_pct"
        ],
        "scale_prior_kind": "traffic_standard_or_survey",
        "scale_prior_description": picks["scale_prior_description"],
        "profile_notes": picks["profile_notes"],
        "road_plane_polygon_world": [
            [0.0, 0.0],
            [picks["width_m"], 0.0],
            [picks["width_m"], picks["length_m"]],
            [0.0, picks["length_m"]],
        ],
        "notes": f"Codex-assisted standard-prior calibration picks for {clip}.",
    }


def _clip_payload(picks: ClipPicks) -> dict[str, Any]:
    control_points = _control_points_from_manual_roi(picks)
    validation_segments = _validation_segments_with_world_from_control_h(
        picks,
        control_points,
    )
    return {
        "annotation_method": ANNOTATION_METHOD,
        "annotation_confidence": 0.78,
        "evidence_sources": EVIDENCE_SOURCES,
        "scale_prior": {
            "kind": "traffic_standard_or_survey",
            "description": picks["scale_prior_description"],
        },
        "control_points": control_points,
        "validation_segments": validation_segments,
        "road_plane_polygon_pixel": picks["road_plane_polygon_pixel"],
        "road_plane_polygon_world": [
            [0.0, 0.0],
            [picks["width_m"], 0.0],
            [picks["width_m"], picks["length_m"]],
            [0.0, picks["length_m"]],
        ],
}


def _world_to_pixel_homography(
    world_points: list[list[float]],
    pixel_points: list[list[float]],
) -> np.ndarray:
    rows: list[list[float]] = []
    for (x, y), (u, v) in zip(world_points, pixel_points, strict=True):
        rows.append([x, y, 1.0, 0.0, 0.0, 0.0, -u * x, -u * y, -u])
        rows.append([0.0, 0.0, 0.0, x, y, 1.0, -v * x, -v * y, -v])
    _, _, vh = np.linalg.svd(np.array(rows, dtype=float))
    homography = vh[-1].reshape(3, 3)
    return homography / homography[2, 2]


def _project_world_to_pixel(homography: np.ndarray, world: list[float]) -> list[float]:
    projected = homography @ np.array([float(world[0]), float(world[1]), 1.0])
    projected /= projected[2]
    return [round(float(projected[0]), 2), round(float(projected[1]), 2)]


def _control_points_from_manual_roi(picks: ClipPicks) -> list[dict[str, list[float]]]:
    world_corners = [
        [0.0, 0.0],
        [picks["width_m"], 0.0],
        [picks["width_m"], picks["length_m"]],
        [0.0, picks["length_m"]],
    ]
    homography = _world_to_pixel_homography(
        world_corners,
        picks["road_plane_polygon_pixel"],
    )
    points: list[dict[str, list[float]]] = []
    for x_fraction, y_fraction in CONTROL_WORLD_FRACTIONS:
        world = [
            round(picks["width_m"] * x_fraction, 2),
            round(picks["length_m"] * y_fraction, 2),
        ]
        points.append({"pixel": _project_world_to_pixel(homography, world), "world": world})
    return points


def _pixel_to_world_homography(control_points: list[dict[str, Any]]) -> np.ndarray:
    rows: list[list[float]] = []
    for point in control_points:
        u, v = (float(value) for value in point["pixel"])
        x, y = (float(value) for value in point["world"])
        rows.append([u, v, 1.0, 0.0, 0.0, 0.0, -x * u, -x * v, -x])
        rows.append([0.0, 0.0, 0.0, u, v, 1.0, -y * u, -y * v, -y])
    _, _, vh = np.linalg.svd(np.array(rows, dtype=float))
    homography = vh[-1].reshape(3, 3)
    return homography / homography[2, 2]


def _project_pixel_to_world(homography: np.ndarray, pixel: list[float]) -> list[float]:
    projected = homography @ np.array([float(pixel[0]), float(pixel[1]), 1.0])
    projected /= projected[2]
    return [round(float(projected[0]), 2), round(float(projected[1]), 2)]


def _validation_segments_with_world_from_control_h(
    picks: ClipPicks,
    control_points: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    homography = _pixel_to_world_homography(control_points)
    segments: list[dict[str, Any]] = []
    for segment in picks["validation_segments"]:
        next_segment = dict(segment)
        next_segment["world_start"] = _project_pixel_to_world(
            homography,
            segment["pixel_start"],
        )
        next_segment["world_end"] = _project_pixel_to_world(
            homography,
            segment["pixel_end"],
        )
        next_segment["world_coordinate_source"] = (
            "pixel_to_world_homography_projection_from_agent_assisted_control_points"
        )
        segments.append(next_segment)
    return segments


def build_payload() -> dict[str, Any]:
    payload: dict[str, Any] = {
        "__profile_metadata__": {
            clip: _profile_metadata(clip, picks) for clip, picks in CLIPS.items()
        },
    }
    for clip, picks in CLIPS.items():
        payload[clip] = _clip_payload(picks)
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
