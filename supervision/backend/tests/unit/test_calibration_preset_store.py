from __future__ import annotations

from pathlib import Path

import yaml
from application.services.calibration_preset_store import CalibrationPresetStore


def test_calibration_preset_store_saves_video_manual_preset(tmp_path: Path) -> None:
    preset_path = tmp_path / "calibration_presets.yaml"
    preset_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "scene_profiles": {"demo": {"world_width_m": 10.0}},
                "video_calibrations": {},
            },
        ),
        encoding="utf-8",
    )
    store = CalibrationPresetStore(preset_path)

    saved = store.upsert_entry(
        "demo.mp4",
        {
            "notes": "surveyed stop-line calibration",
            "position_rmse_floor_m": 0.4,
            "calibration_scale_uncertainty_pct": 3.0,
            "points": [
                {"pixel_x": 100, "pixel_y": 600, "world_x": 0, "world_y": 0},
                {"pixel_x": 500, "pixel_y": 600, "world_x": 20, "world_y": 0},
                {"pixel_x": 450, "pixel_y": 300, "world_x": 20, "world_y": 60},
                {"pixel_x": 150, "pixel_y": 300, "world_x": 0, "world_y": 60},
            ],
        },
        frame_width=1280,
        frame_height=720,
        grid_spacing_m=10.0,
    )

    assert saved["source"] == "video_manual_preset"
    assert saved["diagnostics"]["calibration_source"] == "video_manual_preset"
    assert saved["diagnostics"]["inlier_count"] == 4
    assert (
        saved["diagnostics"]["homography_grid"]["generated_from"]
        == "inverse_homography_projection"
    )
    reloaded = yaml.safe_load(preset_path.read_text(encoding="utf-8"))
    assert reloaded["scene_profiles"]["demo"]["world_width_m"] == 10.0
    assert reloaded["video_calibrations"]["demo.mp4"]["notes"] == "surveyed stop-line calibration"


def test_calibration_preset_store_rejects_collinear_points(tmp_path: Path) -> None:
    store = CalibrationPresetStore(tmp_path / "calibration_presets.yaml")

    try:
        store.upsert_entry(
            "bad.mp4",
            {
                "points": [
                    {"pixel_x": 0, "pixel_y": 0, "world_x": 0, "world_y": 0},
                    {"pixel_x": 1, "pixel_y": 1, "world_x": 1, "world_y": 1},
                    {"pixel_x": 2, "pixel_y": 2, "world_x": 2, "world_y": 2},
                    {"pixel_x": 3, "pixel_y": 3, "world_x": 3, "world_y": 3},
                ],
            },
        )
    except ValueError as exc:
        assert "collinear" in str(exc)
    else:
        raise AssertionError("collinear calibration points should be rejected")
