from __future__ import annotations

import json
from pathlib import Path

from scripts.validate_calibration_presets import render_markdown, validate_catalog


def test_validate_catalog_reports_missing_manual_presets(tmp_path: Path) -> None:
    preset_path = tmp_path / "calibration_presets.json"
    preset_path.write_text(json.dumps({"scene_profiles": {}, "video_calibrations": {}}))

    summary = validate_catalog(
        preset_path,
        required_clips=["028_red_light_static_0008s_30s.mp4"],
    )
    markdown = render_markdown(summary)

    assert summary["video_calibration_count"] == 0
    assert summary["pass_count"] == 0
    assert summary["industrial_readiness"] == "not_ready"
    assert summary["missing_required_clips"] == ["028_red_light_static_0008s_30s.mp4"]
    assert "No per-video manual calibration presets" in markdown
    assert "Missing Required Manual Calibrations" in markdown


def test_validate_catalog_passes_valid_manual_preset(tmp_path: Path) -> None:
    preset_path = tmp_path / "calibration_presets.json"
    preset_path.write_text(
        json.dumps(
            {
                "scene_profiles": {},
                "video_calibrations": {
                    "clip.mp4": {
                        "position_rmse_floor_m": 0.5,
                        "calibration_scale_uncertainty_pct": 3.0,
                        "points": [
                            {"pixel_x": 0, "pixel_y": 100, "world_x": 0, "world_y": 0},
                            {"pixel_x": 100, "pixel_y": 100, "world_x": 10, "world_y": 0},
                            {"pixel_x": 100, "pixel_y": 0, "world_x": 10, "world_y": 20},
                            {"pixel_x": 0, "pixel_y": 0, "world_x": 0, "world_y": 20},
                        ],
                    },
                },
            },
        ),
    )

    summary = validate_catalog(preset_path, required_clips=["clip.mp4"])

    assert summary["pass_count"] == 1
    assert summary["fail_count"] == 0
    assert summary["industrial_readiness"] == "ready"
    assert summary["missing_required_clips"] == []
    assert summary["rows"][0]["calibration_quality"] == "excellent"


def test_validate_catalog_fails_too_few_points(tmp_path: Path) -> None:
    preset_path = tmp_path / "calibration_presets.json"
    preset_path.write_text(
        json.dumps(
            {
                "scene_profiles": {},
                "video_calibrations": {
                    "clip.mp4": {
                        "position_rmse_floor_m": 0.5,
                        "calibration_scale_uncertainty_pct": 3.0,
                        "points": [
                            {"pixel_x": 0, "pixel_y": 0, "world_x": 0, "world_y": 0},
                            {"pixel_x": 1, "pixel_y": 1, "world_x": 1, "world_y": 1},
                        ],
                    },
                },
            },
        ),
    )

    summary = validate_catalog(preset_path)

    assert summary["fail_count"] == 1
    assert "too_few_points" in summary["rows"][0]["issues"]


def test_validate_catalog_marks_required_failed_preset_not_ready(tmp_path: Path) -> None:
    preset_path = tmp_path / "calibration_presets.json"
    preset_path.write_text(
        json.dumps(
            {
                "scene_profiles": {},
                "video_calibrations": {
                    "clip.mp4": {
                        "position_rmse_floor_m": 0.5,
                        "calibration_scale_uncertainty_pct": 3.0,
                        "points": [
                            {"pixel_x": 0, "pixel_y": 0, "world_x": 0, "world_y": 0},
                            {"pixel_x": 1, "pixel_y": 1, "world_x": 1, "world_y": 1},
                        ],
                    },
                },
            },
        ),
    )

    summary = validate_catalog(preset_path, required_clips=["clip.mp4"])

    assert summary["industrial_readiness"] == "not_ready"
    assert "required_video_calibration_failed" in summary["readiness_issues"]


def test_validate_catalog_rejects_template_points_as_not_manual(tmp_path: Path) -> None:
    preset_path = tmp_path / "calibration_presets.json"
    preset_path.write_text(
        json.dumps(
            {
                "scene_profiles": {},
                "video_calibrations": {
                    "clip.mp4": {
                        "notes": "Replace pixel_x/pixel_y template points before claiming speed.",
                        "position_rmse_floor_m": 0.5,
                        "calibration_scale_uncertainty_pct": 3.0,
                        "points": [
                            {"pixel_x": 0, "pixel_y": 100, "world_x": 0, "world_y": 0},
                            {"pixel_x": 100, "pixel_y": 100, "world_x": 10, "world_y": 0},
                            {"pixel_x": 100, "pixel_y": 0, "world_x": 10, "world_y": 20},
                            {"pixel_x": 0, "pixel_y": 0, "world_x": 0, "world_y": 20},
                        ],
                    },
                },
            },
        ),
    )

    summary = validate_catalog(preset_path, required_clips=["clip.mp4"])

    assert summary["industrial_readiness"] == "not_ready"
    assert "template_points_not_manual" in summary["rows"][0]["issues"]
