from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from scripts.prepare_calibration_assets import (
    build_template_points,
    draw_calibration_preview,
    prepare_assets,
)


def test_build_template_points_uses_trapezoid_ground_plane_defaults() -> None:
    points = build_template_points(
        width=1280,
        height=720,
        world_width_m=28.0,
        world_length_m=75.0,
    )

    assert points == [
        {"pixel_x": 256.0, "pixel_y": 662.4, "world_x": 0.0, "world_y": 0.0},
        {"pixel_x": 1100.8, "pixel_y": 662.4, "world_x": 28.0, "world_y": 0.0},
        {"pixel_x": 793.6, "pixel_y": 316.8, "world_x": 28.0, "world_y": 75.0},
        {"pixel_x": 486.4, "pixel_y": 316.8, "world_x": 0.0, "world_y": 75.0},
    ]


def test_draw_calibration_preview_marks_control_points() -> None:
    frame = np.zeros((120, 160, 3), dtype=np.uint8)
    points = build_template_points(
        width=160,
        height=120,
        world_width_m=10.0,
        world_length_m=20.0,
    )

    preview = draw_calibration_preview(frame, points)

    assert preview.shape == frame.shape
    assert int(preview.sum()) > 0


def test_prepare_assets_rejects_missing_explicit_clip(tmp_path: Path) -> None:
    input_dir = tmp_path / "videos"
    input_dir.mkdir()
    (input_dir / "a.mp4").write_text("")

    with pytest.raises(ValueError, match="missing.mp4"):
        prepare_assets(
            input_dir=input_dir,
            output_dir=tmp_path / "out",
            limit=1,
            frame_index=1,
            clip_names=["missing.mp4"],
        )
