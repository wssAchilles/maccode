from __future__ import annotations

from pathlib import Path

from domain.auto_calibration.service import AutoCalibrationService
from scripts.analyze_real_videos import (
    CameraProfilePreset,
    load_camera_profiles,
    match_camera_profile,
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
