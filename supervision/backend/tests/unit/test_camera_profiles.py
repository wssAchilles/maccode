from __future__ import annotations

from pathlib import Path

from domain.auto_calibration.service import AutoCalibrationService
from domain.calibration.models import CalibrationPoint
from scripts.analyze_real_videos import (
    CameraProfilePreset,
    VideoCalibrationPreset,
    load_camera_profiles,
    match_camera_profile,
    runtime_metric_planes,
)


def _match(name: str, profiles: dict[str, CameraProfilePreset]) -> CameraProfilePreset:
    profile = match_camera_profile(Path(name), profiles)
    assert profile is not None
    return profile


def test_camera_profiles_match_fixed_camera_clip_families() -> None:
    profiles = load_camera_profiles(Path("data/tests/camera_profiles.yaml"))

    assert _match("024_complex_signal_day_wide_0045s_30s.mp4", profiles).profile_id == (
        "jackson_hole_signal_camera"
    )
    assert _match("027_complex_signal_day_wide_0150s_30s.mp4", profiles).profile_id == (
        "jackson_hole_signal_camera"
    )
    assert _match("034_pedestrian_crowd_high_view_0030s_30s.mp4", profiles).profile_id == (
        "pedestrian_high_view_camera"
    )
    assert _match("040_pedestrian_crowd_high_view_0210s_30s.mp4", profiles).profile_id == (
        "pedestrian_high_view_camera"
    )
    assert _match("060_dense_city_traffic_4k_elevated_0210s_30s.mp4", profiles).profile_id == (
        "dense_city_4k_camera"
    )
    assert _match("065_dense_city_traffic_4k_elevated_0360s_30s.mp4", profiles).profile_id == (
        "dense_city_4k_camera"
    )


def test_pedestrian_profile_covers_same_camera_training_family_033_to_042() -> None:
    profiles = load_camera_profiles(Path("data/tests/camera_profiles.yaml"))

    for clip_id in range(33, 43):
        offset_sec = (clip_id - 33) * 30
        clip_name = (
            f"{clip_id:03d}_pedestrian_crowd_high_view_{offset_sec:04d}s_30s.mp4"
        )

        assert _match(clip_name, profiles).profile_id == "pedestrian_high_view_camera"

    assert _match(
        "041_pedestrian_crowd_high_view_0240s_30s.mp4",
        profiles,
    ).profile_id == "pedestrian_high_view_camera"


def test_dense_city_profile_covers_vehicle_regression_family_053_to_065() -> None:
    profiles = load_camera_profiles(Path("data/tests/camera_profiles.yaml"))

    for clip_id in range(53, 66):
        offset_sec = (clip_id - 53) * 30
        clip_name = (
            f"{clip_id:03d}_dense_city_traffic_4k_elevated_{offset_sec:04d}s_30s.mp4"
        )

        assert _match(clip_name, profiles).profile_id == "dense_city_4k_camera"

    assert _match(
        "063_dense_city_traffic_4k_elevated_0300s_30s.mp4",
        profiles,
    ).profile_id == "dense_city_4k_camera"


def test_camera_profile_has_auto_calibration_candidates() -> None:
    profiles = load_camera_profiles(Path("data/tests/camera_profiles.yaml"))
    profile = profiles["jackson_hole_signal_camera"]

    assert profile.manual_control_points
    assert profile.calibration_trusted is True
    assert profile.road_plane_polygon_world
    assert profile.validation_segments
    assert profile.auto_candidate_lines
    assert profile.quality_gates["min_auto_confidence_for_auto_use"] == 0.75
    assert profile.camera_intrinsics_prior["fov_deg"] > 0
    assert profile.camera_mount_prior["height_m"] > 0
    assert profile.vehicle_3d_priors["car"]["length_m"] == 4.5
    assert profile.vehicle_3d_observations


def test_pedestrian_camera_profile_declares_person_metric_plane() -> None:
    profiles = load_camera_profiles(Path("data/tests/camera_profiles.yaml"))
    profile = profiles["pedestrian_high_view_camera"]

    assert profile.metric_planes
    plane = profile.metric_planes[0]
    assert plane["plane_id"] == "pedestrian_corridor"
    assert plane["plane_kind"] == "person_corridor"
    assert plane["trusted"] is True
    assert len(plane["control_points"]) >= 4
    assert plane["pixel_polygon"]
    assert plane["world_polygon"]


def test_empty_video_metric_planes_fall_back_to_camera_profile() -> None:
    profiles = load_camera_profiles(Path("data/tests/camera_profiles.yaml"))
    profile = profiles["pedestrian_high_view_camera"]
    video_preset = VideoCalibrationPreset(
        clip="042_pedestrian_crowd_high_view_0270s_30s.mp4",
        points=[
            CalibrationPoint(0.0, 1048.0, 0.0, 0.0),
            CalibrationPoint(1060.0, 1070.0, 12.0, 0.0),
            CalibrationPoint(1540.0, 0.0, 12.0, 45.0),
            CalibrationPoint(560.0, 0.0, 0.0, 45.0),
        ],
        position_rmse_floor_m=1.2,
        calibration_scale_uncertainty_pct=10.0,
        calibration_trusted=True,
        road_plane_polygon_world=[(0.0, 0.0), (12.0, 0.0), (12.0, 45.0), (0.0, 45.0)],
        validation_segments=[],
        notes="test",
        metric_planes=[],
    )

    assert runtime_metric_planes(video_preset, profile) == profile.metric_planes


def test_auto_calibration_candidates_fallback_to_manual_profile() -> None:
    profiles = load_camera_profiles(Path("data/tests/camera_profiles.yaml"))
    profile = profiles["jackson_hole_signal_camera"]

    diagnostics = AutoCalibrationService().diagnose(
        profile.auto_candidate_lines,
        profile.scale_prior_used,
        manual_profile_available=True,
        evidence_sources=["camera_profile_candidates"],
        world_width_m=profile.world_width_m,
        world_length_m=profile.world_length_m,
    )

    assert diagnostics.confidence < profile.quality_gates["min_auto_confidence_for_auto_use"]
    assert diagnostics.selected_strategy == "manual_camera_profile_fallback"
    assert diagnostics.evidence_sources == ["camera_profile_candidates"]
    assert diagnostics.homography_proposal is not None
    assert diagnostics.homography_proposal.method == "candidate_trapezoid_dlt_ransac"
    assert "auto_confidence_below_manual_profile_gate" in diagnostics.quality_issues
