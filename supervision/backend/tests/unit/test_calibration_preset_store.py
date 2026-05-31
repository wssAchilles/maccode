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
            "calibration_trusted": True,
            "scale_prior": {
                "kind": "survey",
                "description": "measured stop-line width",
            },
            "profile_notes": "fixed camera, flat road plane",
            "road_plane_polygon_pixel": [[100, 600], [500, 600], [450, 300], [150, 300]],
            "road_plane_polygon_world": [[0, 0], [20, 0], [20, 60], [0, 60]],
            "validation_segments": [
                {
                    "name": "independent_midline",
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
            ],
        },
        frame_width=1280,
        frame_height=720,
        grid_spacing_m=10.0,
    )

    assert saved["source"] == "video_manual_preset"
    assert saved["diagnostics"]["calibration_source"] == "video_manual_preset"
    assert saved["diagnostics"]["calibration_trusted"] is True
    assert saved["diagnostics"]["validation_max_error_px"] < 1e-6
    assert saved["diagnostics"]["independent_validation_segment_count"] == 2
    assert saved["diagnostics"]["inlier_count"] == 4
    assert (
        saved["diagnostics"]["homography_grid"]["generated_from"]
        == "inverse_homography_projection"
    )
    reloaded = yaml.safe_load(preset_path.read_text(encoding="utf-8"))
    assert reloaded["schema_version"] == 2
    assert reloaded["scene_profiles"]["demo"]["world_width_m"] == 10.0
    assert reloaded["video_calibrations"]["demo.mp4"]["notes"] == "surveyed stop-line calibration"
    assert reloaded["video_calibrations"]["demo.mp4"]["calibration_trusted"] is True
    assert reloaded["video_calibrations"]["demo.mp4"]["scale_prior"]["kind"] == "survey"
    assert (
        reloaded["video_calibrations"]["demo.mp4"]["profile_notes"]
        == "fixed camera, flat road plane"
    )
    assert reloaded["video_calibrations"]["demo.mp4"]["road_plane_polygon_pixel"] == [
        [100.0, 600.0],
        [500.0, 600.0],
        [450.0, 300.0],
        [150.0, 300.0],
    ]


def test_calibration_preset_store_preserves_vehicle_3d_priors_and_diagnostics(
    tmp_path: Path,
) -> None:
    store = CalibrationPresetStore(tmp_path / "calibration_presets.yaml")

    saved = store.upsert_entry(
        "demo.mp4",
        {
            "calibration_trusted": False,
            "camera_intrinsics_prior": {
                "fx": 1000.0,
                "fy": 1000.0,
                "cx": 640.0,
                "cy": 360.0,
                "fx_bounds_scale": [0.5, 2.0],
                "confidence": 0.8,
            },
            "camera_mount_prior": {
                "height_m": 7.0,
                "height_sigma_m": 1.0,
            },
            "vehicle_3d_priors": {
                "car": {
                    "length_m": 4.5,
                    "width_m": 1.8,
                    "height_m": 1.5,
                }
            },
            "vehicle_3d_observations": [
                {
                    "frame_index": 1,
                    "class_name": "car",
                    "bbox_xyxy": [500.0, 360.0, 620.0, 480.0],
                    "lane_direction_deg": 12.0,
                }
            ],
            "points": [
                {"pixel_x": 100, "pixel_y": 600, "world_x": 0, "world_y": 0},
                {"pixel_x": 500, "pixel_y": 600, "world_x": 20, "world_y": 0},
                {"pixel_x": 450, "pixel_y": 300, "world_x": 20, "world_y": 60},
                {"pixel_x": 150, "pixel_y": 300, "world_x": 0, "world_y": 60},
            ],
        },
        frame_width=1280,
        frame_height=720,
    )

    diagnostics = saved["diagnostics"]["calibration_3d_diagnostics"]

    assert saved["entry"]["vehicle_3d_priors"]["car"]["length_m"] == 4.5
    assert diagnostics["calibration_source"] == "vehicle_3d_prior_pnp"
    assert diagnostics["calibration_trusted"] is False
    assert "bbox_only_observations_below_minimum" in diagnostics["quality_issues"]


def test_calibration_preset_store_suppresses_grid_without_validation(tmp_path: Path) -> None:
    store = CalibrationPresetStore(tmp_path / "calibration_presets.yaml")

    saved = store.upsert_entry(
        "demo.mp4",
        {
            "calibration_trusted": True,
            "points": [
                {"pixel_x": 100, "pixel_y": 600, "world_x": 0, "world_y": 0},
                {"pixel_x": 500, "pixel_y": 600, "world_x": 20, "world_y": 0},
                {"pixel_x": 450, "pixel_y": 300, "world_x": 20, "world_y": 60},
                {"pixel_x": 150, "pixel_y": 300, "world_x": 0, "world_y": 60},
            ],
        },
        frame_width=1280,
        frame_height=720,
    )

    assert saved["diagnostics"]["calibration_trusted"] is False
    assert saved["entry"]["calibration_trusted"] is False
    assert "homography_grid" not in saved["diagnostics"]
    assert (
        "untrusted_calibration_grid_suppressed"
        in saved["diagnostics"]["error_sources"]
    )


def test_calibration_preset_store_persists_untrusted_when_declared_trusted_fails(
    tmp_path: Path,
) -> None:
    preset_path = tmp_path / "calibration_presets.yaml"
    store = CalibrationPresetStore(preset_path)

    saved = store.upsert_entry(
        "demo.mp4",
        {
            "calibration_trusted": True,
            "points": [
                {"pixel_x": 100, "pixel_y": 600, "world_x": 0, "world_y": 0},
                {"pixel_x": 500, "pixel_y": 600, "world_x": 20, "world_y": 0},
                {"pixel_x": 450, "pixel_y": 300, "world_x": 20, "world_y": 60},
                {"pixel_x": 150, "pixel_y": 300, "world_x": 0, "world_y": 60},
            ],
        },
        frame_width=1280,
        frame_height=720,
    )

    reloaded = yaml.safe_load(preset_path.read_text(encoding="utf-8"))
    assert saved["diagnostics"]["declared_calibration_trusted"] is True
    assert saved["diagnostics"]["calibration_trusted"] is False
    assert saved["entry"]["calibration_trusted"] is False
    assert reloaded["video_calibrations"]["demo.mp4"]["calibration_trusted"] is False


def test_calibration_preset_store_rejects_visual_prior_provenance(
    tmp_path: Path,
) -> None:
    store = CalibrationPresetStore(tmp_path / "calibration_presets.yaml")

    saved = store.upsert_entry(
        "demo.mp4",
        {
            "calibration_trusted": True,
            "annotation_method": "agent_cv_geometry_prior_homography",
            "evidence_sources": ["opencv_canny_hough_line_candidates"],
            "scale_prior": {
                "kind": "traffic_standard_visual_prior",
                "description": "visual-prior, not a field survey",
            },
            "profile_notes": "fixed camera, flat road plane",
            "road_plane_polygon_pixel": [[100, 600], [500, 600], [450, 300], [150, 300]],
            "road_plane_polygon_world": [[0, 0], [20, 0], [20, 60], [0, 60]],
            "validation_segments": [
                {
                    "name": "independent_midline",
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
            ],
        },
        frame_width=1280,
        frame_height=720,
    )

    assert saved["diagnostics"]["provenance_trusted"] is False
    assert saved["diagnostics"]["provenance_issues"]
    assert saved["diagnostics"]["calibration_trusted"] is False
    assert "homography_grid" not in saved["diagnostics"]


def test_calibration_preset_store_rejects_reused_control_points_as_validation(
    tmp_path: Path,
) -> None:
    store = CalibrationPresetStore(tmp_path / "calibration_presets.yaml")

    saved = store.upsert_entry(
        "demo.mp4",
        {
            "calibration_trusted": True,
            "validation_segments": [
                {
                    "name": "reused_stop_line",
                    "pixel_start": [100, 600],
                    "pixel_end": [500, 600],
                    "world_start": [0, 0],
                    "world_end": [20, 0],
                },
            ],
            "points": [
                {"pixel_x": 100, "pixel_y": 600, "world_x": 0, "world_y": 0},
                {"pixel_x": 500, "pixel_y": 600, "world_x": 20, "world_y": 0},
                {"pixel_x": 450, "pixel_y": 300, "world_x": 20, "world_y": 60},
                {"pixel_x": 150, "pixel_y": 300, "world_x": 0, "world_y": 60},
            ],
        },
        frame_width=1280,
        frame_height=720,
    )

    assert saved["diagnostics"]["validation_max_error_px"] < 1e-6
    assert saved["diagnostics"]["independent_validation_segment_count"] == 0
    assert saved["diagnostics"]["calibration_trusted"] is False
    assert saved["entry"]["calibration_trusted"] is False
    assert "homography_grid" not in saved["diagnostics"]
    assert (
        "validation_segments_reuse_control_points"
        in saved["diagnostics"]["error_sources"]
    )


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
