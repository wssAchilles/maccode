from __future__ import annotations

import json
from pathlib import Path

import pytest
from scripts.merge_calibration_preset import merge_preset


def _valid_profile() -> dict[str, object]:
    return {
        "world_width_m": 10.0,
        "world_length_m": 20.0,
        "position_rmse_floor_m": 0.5,
        "calibration_scale_uncertainty_pct": 3.0,
        "line_y_ratio": 0.7,
        "line_x_start_ratio": 0.2,
        "line_x_end_ratio": 0.8,
        "notes": "test profile",
    }


def _valid_entry() -> dict[str, object]:
    return {
        "position_rmse_floor_m": 0.5,
        "calibration_scale_uncertainty_pct": 3.0,
        "points": [
            {"pixel_x": 0, "pixel_y": 100, "world_x": 0, "world_y": 0},
            {"pixel_x": 100, "pixel_y": 100, "world_x": 10, "world_y": 0},
            {"pixel_x": 100, "pixel_y": 0, "world_x": 10, "world_y": 20},
            {"pixel_x": 0, "pixel_y": 0, "world_x": 0, "world_y": 20},
        ],
    }


def test_merge_preset_preserves_scene_profiles_and_validates_output(tmp_path: Path) -> None:
    base_path = tmp_path / "base.json"
    input_path = tmp_path / "exported.json"
    output_path = tmp_path / "merged.json"
    base_path.write_text(
        json.dumps(
                {
                    "schema_version": 1,
                    "scene_profiles": {"road": _valid_profile()},
                    "video_calibrations": {},
                },
        ),
    )
    input_path.write_text(
        json.dumps({"video_calibrations": {"clip.mp4": _valid_entry()}}),
    )

    summary = merge_preset(
        base_path,
        input_path,
        output_path,
        overwrite=False,
        required_clips=["clip.mp4"],
    )
    merged = json.loads(output_path.read_text())

    assert merged["scene_profiles"] == {"road": _valid_profile()}
    assert "clip.mp4" in merged["video_calibrations"]
    assert summary["validation"]["industrial_readiness"] == "ready"
    assert (tmp_path / "merged_calibration_validation.md").exists()


def test_merge_preset_rejects_duplicate_without_overwrite(tmp_path: Path) -> None:
    base_path = tmp_path / "base.json"
    input_path = tmp_path / "exported.json"
    output_path = tmp_path / "merged.json"
    base_path.write_text(
        json.dumps({"video_calibrations": {"clip.mp4": _valid_entry()}}),
    )
    input_path.write_text(
        json.dumps({"video_calibrations": {"clip.mp4": _valid_entry()}}),
    )

    with pytest.raises(ValueError, match="refusing to overwrite"):
        merge_preset(
            base_path,
            input_path,
            output_path,
            overwrite=False,
            required_clips=["clip.mp4"],
        )


def test_merge_preset_accepts_bare_video_calibration_object(tmp_path: Path) -> None:
    base_path = tmp_path / "base.json"
    input_path = tmp_path / "exported.json"
    output_path = tmp_path / "merged.json"
    base_path.write_text(json.dumps({"video_calibrations": {}}))
    input_path.write_text(json.dumps({"clip.mp4": _valid_entry()}))

    summary = merge_preset(
        base_path,
        input_path,
        output_path,
        overwrite=False,
        required_clips=["clip.mp4"],
    )

    assert summary["merged_clips"] == ["clip.mp4"]
    assert summary["validation"]["industrial_readiness"] == "ready"
