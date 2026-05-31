from __future__ import annotations

from typing import Any, cast

from scripts.promote_video_calibration_to_camera_profile import promote_clip


def _trusted_video_payload(calibration_trusted: bool = True) -> dict[str, object]:
    return {
        "video_calibrations": {
            "026_complex_signal_day_wide_0115s_30s.mp4": {
                "notes": "trusted test calibration",
                "position_rmse_floor_m": 0.4,
                "calibration_scale_uncertainty_pct": 3.0,
                "calibration_trusted": calibration_trusted,
                "scale_prior": {
                    "kind": "survey",
                    "description": "measured 20m stop-line road width",
                },
                "profile_notes": "fixed camera, flat road plane",
                "road_plane_polygon_pixel": [[100, 600], [500, 600], [450, 300], [150, 300]],
                "road_plane_polygon_world": [[0, 0], [20, 0], [20, 60], [0, 60]],
                "validation_segments": [
                    {
                        "name": "independent_stop_line",
                        "pixel_start": [214.28571429, 428.57142857],
                        "pixel_end": [385.71428571, 428.57142857],
                        "world_start": [5, 30],
                        "world_end": [15, 30],
                    },
                    {
                        "name": "independent_near_lane_edge",
                        "pixel_start": [210.0, 480.0],
                        "pixel_end": [390.0, 480.0],
                        "world_start": [5, 20],
                        "world_end": [15, 20],
                    },
                ],
                "points": [
                    {"pixel_x": 100, "pixel_y": 600, "world_x": 0, "world_y": 0},
                    {"pixel_x": 500, "pixel_y": 600, "world_x": 20, "world_y": 0},
                    {"pixel_x": 450, "pixel_y": 300, "world_x": 20, "world_y": 60},
                    {"pixel_x": 150, "pixel_y": 300, "world_x": 0, "world_y": 60},
                    {"pixel_x": 300, "pixel_y": 600, "world_x": 10, "world_y": 0},
                    {"pixel_x": 300, "pixel_y": 300, "world_x": 10, "world_y": 60},
                    {
                        "pixel_x": 205.26315789,
                        "pixel_y": 536.84210526,
                        "world_x": 5,
                        "world_y": 10,
                    },
                    {
                        "pixel_x": 394.73684211,
                        "pixel_y": 536.84210526,
                        "world_x": 15,
                        "world_y": 10,
                    },
                ],
            },
        },
    }


def _camera_payload() -> dict[str, object]:
    return {
        "camera_profiles": {
            "jackson_hole_signal_camera": {
                "display_name": "camera",
                "role": "vehicle_speed",
                "covered_clip_patterns": ["02[3-7]_complex_signal_day_wide_*_30s.mp4"],
                "world_width_m": 28.0,
                "world_length_m": 75.0,
                "grid_spacing_m": 5.0,
                "position_rmse_floor_m": 1.3,
                "calibration_scale_uncertainty_pct": 6.0,
                "calibration_trusted": False,
                "manual_control_points": [],
            },
        },
    }


def test_promote_clip_blocks_untrusted_video_calibration() -> None:
    result, next_payload = promote_clip(
        "026_complex_signal_day_wide_0115s_30s.mp4",
        _trusted_video_payload(calibration_trusted=False),
        _camera_payload(),
    )

    assert result["status"] == "blocked"
    profile = next_payload["camera_profiles"]["jackson_hole_signal_camera"]
    assert profile["calibration_trusted"] is False


def test_promote_clip_updates_camera_profile_after_validation_passes() -> None:
    result, next_payload = promote_clip(
        "026_complex_signal_day_wide_0115s_30s.mp4",
        _trusted_video_payload(),
        _camera_payload(),
    )

    assert result["status"] == "promoted"
    profile = next_payload["camera_profiles"]["jackson_hole_signal_camera"]
    assert profile["calibration_trusted"] is True
    assert len(profile["manual_control_points"]) == 8
    assert profile["world_width_m"] == 20.0
    assert profile["world_length_m"] == 60.0
    assert profile["scale_prior"]["kind"] == "survey"
    assert profile["road_plane_polygon_pixel"]


def test_promote_clip_blocks_missing_sampling_evidence() -> None:
    payload = _trusted_video_payload()
    video_calibrations = cast(dict[str, dict[str, Any]], payload["video_calibrations"])
    entry = video_calibrations["026_complex_signal_day_wide_0115s_30s.mp4"]
    entry.pop("scale_prior")

    result, next_payload = promote_clip(
        "026_complex_signal_day_wide_0115s_30s.mp4",
        payload,
        _camera_payload(),
    )

    assert result["status"] == "blocked"
    assert "missing scale_prior" in result["reason"]
    profile = next_payload["camera_profiles"]["jackson_hole_signal_camera"]
    assert profile["calibration_trusted"] is False
