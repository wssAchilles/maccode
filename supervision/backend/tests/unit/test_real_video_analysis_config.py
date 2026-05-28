from __future__ import annotations

import json
from pathlib import Path

from scripts.analyze_real_videos import (
    build_calibration,
    build_sensitivity_report,
    default_profile_for_clip,
    load_calibration_presets,
)


def test_loads_video_manual_calibration_preset(tmp_path: Path) -> None:
    preset_path = tmp_path / "calibration_presets.json"
    preset_path.write_text(
        json.dumps(
            {
                "scene_profiles": {},
                "video_calibrations": {
                    "clip.mp4": {
                        "position_rmse_floor_m": 0.8,
                        "calibration_scale_uncertainty_pct": 4.0,
                        "notes": "surveyed four-point stop-line calibration",
                        "points": [
                            {
                                "pixel_x": 0.0,
                                "pixel_y": 100.0,
                                "world_x": 0.0,
                                "world_y": 0.0,
                            },
                            {
                                "pixel_x": 100.0,
                                "pixel_y": 100.0,
                                "world_x": 10.0,
                                "world_y": 0.0,
                            },
                            {
                                "pixel_x": 100.0,
                                "pixel_y": 0.0,
                                "world_x": 10.0,
                                "world_y": 20.0,
                            },
                            {
                                "pixel_x": 0.0,
                                "pixel_y": 0.0,
                                "world_x": 0.0,
                                "world_y": 20.0,
                            },
                        ],
                    },
                },
            },
        ),
    )

    catalog = load_calibration_presets(preset_path)

    video_preset = catalog.video_calibrations["clip.mp4"]
    assert video_preset.position_rmse_floor_m == 0.8
    assert video_preset.calibration_scale_uncertainty_pct == 4.0
    assert len(video_preset.points) == 4


def test_manual_calibration_overrides_scene_profile_homography() -> None:
    profile = default_profile_for_clip(Path("023_complex_signal_day_wide_0010s_30s.mp4"))
    catalog = load_calibration_presets(
        Path("data/tests/calibration_presets.json"),
    )
    example = catalog.video_calibrations.get("missing.mp4")

    calibration = build_calibration(1280, 720, profile, example)

    assert calibration.calibration_quality == "excellent"
    assert calibration.inlier_count >= 4


def test_sensitivity_report_scales_speed_band_linearly() -> None:
    report = {
        "active_tracks": [{"speed_kmh": 10.0}, {"speed_kmh": 20.0}],
        "traffic_flow": {"space_mean_speed_kmh": 15.0},
    }

    sensitivity = build_sensitivity_report(report, scale_uncertainty_pct=10.0)

    assert sensitivity["speed_band_kmh"] == [9.0, 22.0]
    assert sensitivity["space_mean_speed_band_kmh"] == [13.5, 16.5]
