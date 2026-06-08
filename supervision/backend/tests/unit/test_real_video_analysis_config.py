from __future__ import annotations

import json
from pathlib import Path

import pytest
from domain.calibration.models import CalibrationPoint
from scripts import build_calibration_qa
from scripts.analyze_real_videos import (
    CalibrationPresetCatalog,
    CameraProfilePreset,
    SceneProfile,
    VideoCalibrationPreset,
    build_calibration,
    build_sensitivity_report,
    build_vehicle_3d_diagnostics,
    calibration_notes,
    default_profile_for_clip,
    load_calibration_presets,
    profile_reuse_note,
    select_clips,
    summarize,
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


def test_loads_yaml_video_manual_calibration_preset(tmp_path: Path) -> None:
    preset_path = tmp_path / "calibration_presets.yaml"
    preset_path.write_text(
        """
scene_profiles: {}
video_calibrations:
  clip.mp4:
    position_rmse_floor_m: 0.6
    calibration_scale_uncertainty_pct: 3.5
    notes: surveyed YAML control points
    points:
      - pixel_x: 0.0
        pixel_y: 100.0
        world_x: 0.0
        world_y: 0.0
      - pixel_x: 100.0
        pixel_y: 100.0
        world_x: 10.0
        world_y: 0.0
      - pixel_x: 100.0
        pixel_y: 0.0
        world_x: 10.0
        world_y: 20.0
      - pixel_x: 0.0
        pixel_y: 0.0
        world_x: 0.0
        world_y: 20.0
""",
    )

    catalog = load_calibration_presets(preset_path)

    video_preset = catalog.video_calibrations["clip.mp4"]
    assert video_preset.position_rmse_floor_m == 0.6
    assert video_preset.calibration_scale_uncertainty_pct == 3.5
    assert video_preset.notes == "surveyed YAML control points"


def test_summarize_includes_vehicle_speed_aggregate() -> None:
    summary = summarize(
        [
            {
                "status": "ok",
                "final_report": {
                    "active_tracks": [
                        {
                            "speed_kmh": 40.0,
                            "physics_valid": True,
                            "speed_confidence": 0.8,
                        },
                    ],
                },
                "vehicle_speed_audit": {
                    "clip": "063_dense_city.mp4",
                    "vehicle_track_samples": 100,
                    "displayable_vehicle_track_samples": 100,
                    "vehicle_display_coverage": 1.0,
                    "max_speed_by_class": {"car": 50.0},
                },
            },
        ],
    )

    aggregate = summary["vehicle_speed_aggregate"]
    assert aggregate["vehicle_track_samples"] == 100
    assert aggregate["vehicle_display_coverage"] == 1.0
    assert aggregate["passes_dense_city_acceptance"] is True


def test_calibration_yaml_schema_version_tracks_v2_contract() -> None:
    assert "schema_version: 2" in Path("data/tests/calibration_presets.yaml").read_text(
        encoding="utf-8",
    )
    assert "schema_version: 2" in Path("data/tests/camera_profiles.yaml").read_text(
        encoding="utf-8",
    )


def test_loads_trusted_manual_calibration_metadata(tmp_path: Path) -> None:
    preset_path = tmp_path / "calibration_presets.yaml"
    preset_path.write_text(
        """
scene_profiles: {}
video_calibrations:
  clip.mp4:
    position_rmse_floor_m: 0.6
    calibration_scale_uncertainty_pct: 3.5
    notes: trusted surveyed calibration
    calibration_trusted: true
    road_plane_polygon_world:
      - [0.0, 0.0]
      - [10.0, 0.0]
      - [10.0, 20.0]
      - [0.0, 20.0]
    validation_segments:
      - name: stop_line
        pixel_start: [0.0, 100.0]
        pixel_end: [100.0, 100.0]
        world_start: [0.0, 0.0]
        world_end: [10.0, 0.0]
    points:
      - pixel_x: 0.0
        pixel_y: 100.0
        world_x: 0.0
        world_y: 0.0
      - pixel_x: 100.0
        pixel_y: 100.0
        world_x: 10.0
        world_y: 0.0
      - pixel_x: 100.0
        pixel_y: 0.0
        world_x: 10.0
        world_y: 20.0
      - pixel_x: 0.0
        pixel_y: 0.0
        world_x: 0.0
        world_y: 20.0
""",
    )

    catalog = load_calibration_presets(preset_path)
    video_preset = catalog.video_calibrations["clip.mp4"]

    assert video_preset.calibration_trusted is True
    assert video_preset.road_plane_polygon_world == [
        (0.0, 0.0),
        (10.0, 0.0),
        (10.0, 20.0),
        (0.0, 20.0),
    ]
    assert video_preset.validation_segments[0]["name"] == "stop_line"


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


def test_vehicle_3d_diagnostics_are_built_from_runtime_profile_priors() -> None:
    diagnostics = build_vehicle_3d_diagnostics(
        frame_width=1280,
        frame_height=720,
        camera_intrinsics_prior={
            "fov_deg": 55.0,
            "dist_coeffs": [0.0, 0.0, 0.0, 0.0, 0.0],
            "confidence": 0.7,
        },
        camera_mount_prior={"height_m": 8.0, "height_sigma_m": 1.0},
        vehicle_3d_priors={
            "car": {"length_m": 4.5, "width_m": 1.8, "height_m": 1.5},
        },
        vehicle_3d_observations=[
            {
                "class_name": "car",
                "bbox_xyxy": [420, 320, 520, 410],
                "frame_index": 0,
                "lane_direction_deg": 8.0,
            },
            {
                "class_name": "car",
                "bbox_xyxy": [600, 330, 720, 430],
                "frame_index": 0,
                "lane_direction_deg": 9.0,
            },
            {
                "class_name": "car",
                "bbox_xyxy": [780, 340, 900, 440],
                "frame_index": 0,
                "lane_direction_deg": 7.0,
            },
        ],
    )

    assert diagnostics["calibration_source"] == "vehicle_3d_prior_pnp"
    assert diagnostics["calibration_trusted"] is False
    quality_issues = diagnostics["quality_issues"]
    assert isinstance(quality_issues, list)
    assert "bbox_only_weakly_observable" in quality_issues


def test_select_clips_uses_explicit_clip_names(tmp_path: Path) -> None:
    for name in ["b.mp4", "a.mp4"]:
        (tmp_path / name).write_text("")
    presets = CalibrationPresetCatalog(scene_profiles={}, video_calibrations={})

    selected = select_clips(
        tmp_path,
        limit=1,
        sample_per_profile=0,
        presets=presets,
        clip_names=["b.mp4", "a.mp4"],
    )

    assert [path.name for path in selected] == ["b.mp4", "a.mp4"]


def test_select_clips_rejects_missing_explicit_clip(tmp_path: Path) -> None:
    (tmp_path / "a.mp4").write_text("")
    presets = CalibrationPresetCatalog(scene_profiles={}, video_calibrations={})

    with pytest.raises(ValueError, match="missing.mp4"):
        select_clips(
            tmp_path,
            limit=1,
            sample_per_profile=0,
            presets=presets,
            clip_names=["missing.mp4"],
        )


def test_video_manual_preset_takes_priority_over_camera_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        build_calibration_qa,
        "inspect_video",
        lambda _: {"width": 100, "height": 100, "fps": 30.0, "frame_count": 10},
    )
    video_points = [
        CalibrationPoint(0, 100, 0, 0),
        CalibrationPoint(100, 100, 10, 0),
        CalibrationPoint(100, 0, 10, 10),
        CalibrationPoint(0, 0, 0, 10),
    ]
    camera_points = [
        CalibrationPoint(10, 90, 0, 0),
        CalibrationPoint(90, 90, 20, 0),
        CalibrationPoint(90, 10, 20, 20),
        CalibrationPoint(10, 10, 0, 20),
    ]
    catalog = CalibrationPresetCatalog(
        scene_profiles={
            "wide_signalized_intersection": SceneProfile(
                name="wide_signalized_intersection",
                world_width_m=10,
                world_length_m=10,
                position_rmse_floor_m=0.5,
                calibration_scale_uncertainty_pct=2.0,
                line_y_ratio=0.5,
                line_x_start_ratio=0.1,
                line_x_end_ratio=0.9,
                notes="test",
            )
        },
        video_calibrations={
            "clip.mp4": VideoCalibrationPreset(
                clip="clip.mp4",
                points=video_points,
                position_rmse_floor_m=0.5,
                calibration_scale_uncertainty_pct=2.0,
                calibration_trusted=True,
                road_plane_polygon_world=[(0, 0), (10, 0), (10, 10), (0, 10)],
                validation_segments=[
                    {
                        "name": "video_validation",
                        "pixel_start": [25, 50],
                        "pixel_end": [75, 50],
                        "world_start": [2.5, 5],
                        "world_end": [7.5, 5],
                    },
                    {
                        "name": "video_validation_far",
                        "pixel_start": [25, 25],
                        "pixel_end": [75, 25],
                        "world_start": [2.5, 7.5],
                        "world_end": [7.5, 7.5],
                    }
                ],
                notes="video override",
            )
        },
        camera_profiles={
            "camera": CameraProfilePreset(
                profile_id="camera",
                display_name="camera",
                role="test",
                covered_clip_patterns=["clip.mp4"],
                world_width_m=20,
                world_length_m=20,
                grid_spacing_m=5,
                position_rmse_floor_m=1.0,
                calibration_scale_uncertainty_pct=8.0,
                calibration_trusted=False,
                road_plane_polygon_world=[(0, 0), (20, 0), (20, 20), (0, 20)],
                validation_segments=[],
                manual_control_points=camera_points,
                tuning={},
                traffic_line_zones=[],
                polygon_zones=[],
                traffic_light_rois=[],
                risk_areas=[],
                quality_gates={},
                fallback_policy="camera fallback",
                auto_candidate_lines=[],
                scale_prior_used=None,
            )
        },
    )

    resolved = build_calibration_qa.resolve_calibration(Path("clip.mp4"), catalog)

    assert resolved["source"] == "video_manual_preset"
    assert resolved["declared_trusted"] is True
    assert resolved["calibration_trusted"] is True
    assert resolved["points"] == video_points


def test_video_manual_source_uses_video_notes_and_override_reuse_note() -> None:
    video_preset = VideoCalibrationPreset(
        clip="clip.mp4",
        points=[
            CalibrationPoint(0, 100, 0, 0),
            CalibrationPoint(100, 100, 10, 0),
            CalibrationPoint(100, 0, 10, 10),
            CalibrationPoint(0, 0, 0, 10),
        ],
        position_rmse_floor_m=0.5,
        calibration_scale_uncertainty_pct=2.0,
        calibration_trusted=False,
        road_plane_polygon_world=None,
        validation_segments=[],
        notes="exact video control points still need refinement",
    )
    camera_profile = CameraProfilePreset(
        profile_id="camera",
        display_name="camera",
        role="test",
        covered_clip_patterns=["clip.mp4"],
        world_width_m=20,
        world_length_m=20,
        grid_spacing_m=5,
        position_rmse_floor_m=1.0,
        calibration_scale_uncertainty_pct=8.0,
        calibration_trusted=True,
        road_plane_polygon_world=None,
        validation_segments=[],
        manual_control_points=[
            CalibrationPoint(10, 90, 0, 0),
            CalibrationPoint(90, 90, 20, 0),
            CalibrationPoint(90, 10, 20, 20),
            CalibrationPoint(10, 10, 0, 20),
        ],
        tuning={},
        traffic_line_zones=[],
        polygon_zones=[],
        traffic_light_rois=[],
        risk_areas=[],
        quality_gates={},
        fallback_policy="reuse trusted fixed camera profile",
        auto_candidate_lines=[],
        scale_prior_used=None,
    )
    profile = SceneProfile(
        name="wide_signalized_intersection",
        world_width_m=10,
        world_length_m=10,
        position_rmse_floor_m=0.5,
        calibration_scale_uncertainty_pct=2.0,
        line_y_ratio=0.5,
        line_x_start_ratio=0.1,
        line_x_end_ratio=0.9,
        notes="scene fallback",
    )

    assert (
        calibration_notes(
            "video_manual_preset",
            video_preset,
            camera_profile,
            profile,
        )
        == "exact video control points still need refinement"
    )
    assert profile_reuse_note("video_manual_preset", camera_profile) == (
        "exact video calibration overrides matching fixed-camera profile; "
        "camera profile supplies zones and tuning only"
    )
