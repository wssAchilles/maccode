from __future__ import annotations

from scripts.prepare_calibration_assets import build_template_points


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
