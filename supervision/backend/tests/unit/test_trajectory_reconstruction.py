from __future__ import annotations

import random

import numpy as np
import pytest
from domain.speed.stability import SpeedStabilityMetrics
from domain.speed.trajectory_reconstruction import TrajectoryPoint, TrajectoryReconstructor


def test_reconstruction_stabilizes_uniform_vehicle_with_position_jitter() -> None:
    rng = random.Random(31)
    reconstructor = TrajectoryReconstructor()
    target_speed_mps = 12.0
    points = [
        TrajectoryPoint(
            report_index=frame_index,
            timestamp_sec=frame_index / 30.0,
            world_x=target_speed_mps * frame_index / 30.0 + rng.uniform(-0.45, 0.45),
            world_y=rng.uniform(-0.10, 0.10),
            raw_speed_kmh=None,
        )
        for frame_index in range(120)
    ]

    reconstructed = reconstructor.reconstruct_track(points, class_id=2)
    speeds = [
        float(item["speed_kmh"])
        for item in reconstructed
        if item.get("speed_kmh") is not None
    ]

    assert speeds[-1] == pytest.approx(target_speed_mps * 3.6, abs=3.0)
    assert reconstructed[-1]["speed_cv"] is not None
    assert float(reconstructed[-1]["speed_cv"]) < 0.12
    assert reconstructed[-1]["stability_label"] == "stable"


def test_reconstruction_repairs_short_outlier_jump_without_polluting_speed() -> None:
    reconstructor = TrajectoryReconstructor()
    target_speed_mps = 1.4
    points: list[TrajectoryPoint] = []
    for frame_index in range(90):
        timestamp = frame_index / 30.0
        jump = 20.0 if 42 <= frame_index <= 44 else 0.0
        points.append(
            TrajectoryPoint(
                report_index=frame_index,
                timestamp_sec=timestamp,
                world_x=target_speed_mps * timestamp + jump,
                world_y=0.0,
                raw_speed_kmh=None,
            )
        )

    reconstructed = reconstructor.reconstruct_track(points, class_id=0)
    speeds = [
        float(item["speed_kmh"])
        for item in reconstructed
        if item.get("speed_kmh") is not None
    ]

    assert speeds[-1] == pytest.approx(target_speed_mps * 3.6, abs=0.8)
    assert max(speeds[35:50]) < 10.0
    assert float(reconstructed[-1]["speed_cv"]) < 0.18


def test_reconstruction_rewrites_frame_reports_with_stability_fields() -> None:
    reconstructor = TrajectoryReconstructor()
    reports = []
    for frame_index in range(60):
        timestamp = frame_index / 30.0
        reports.append(
            {
                "frame_index": frame_index,
                "timestamp_sec": timestamp,
                "active_tracks": [
                    {
                        "tracker_id": 9,
                        "class_id": 2,
                        "speed_kmh": 55.0 if frame_index % 2 == 0 else 35.0,
                        "ground_x_m": 10.0 * timestamp,
                        "ground_y_m": 0.0,
                    }
                ],
            }
        )

    updated = reconstructor.reconstruct_reports(reports)
    track = updated[-1]["active_tracks"][0]

    assert track["raw_speed_kmh"] == 35.0
    assert track["speed_stability_score"] is not None
    assert track["speed_cv"] is not None
    assert track["speed_confidence"] is not None
    assert track["speed_uncertainty_kmh"] is not None
    assert track["speed_confidence_interval_kmh"] is not None
    assert track["physics_confidence"] is not None
    assert track["stability_label"] in {"stable", "variable"}


def test_stable_reconstructed_pedestrian_speed_remains_physics_valid() -> None:
    reconstructor = TrajectoryReconstructor()
    reports = []
    for frame_index in range(60):
        timestamp = frame_index / 25.0
        reports.append(
            {
                "frame_index": frame_index,
                "timestamp_sec": timestamp,
                "active_tracks": [
                    {
                        "tracker_id": 40,
                        "class_id": 0,
                        "class_name": "person",
                        "speed_kmh": 5.0,
                        "speed_confidence": 0.72,
                        "speed_uncertainty_kmh": 0.8,
                        "physics_valid": True,
                        "quality_label": "stable",
                        "ground_x_m": 1.4 * timestamp,
                        "ground_y_m": 0.0,
                        "calibration_confidence": 0.25,
                        "contact_confidence": 0.72,
                        "tracking_confidence": 0.85,
                        "occlusion_confidence": 0.9,
                    }
                ],
            }
        )

    updated = reconstructor.reconstruct_reports(reports)
    track = updated[-1]["active_tracks"][0]

    assert track["speed_kmh"] == pytest.approx(5.04, abs=0.8)
    assert track["quality_label"] == "stable"
    assert track["physics_valid"] is True
    assert track["confidence_rejection_reason"] is None


def test_variable_reconstructed_pedestrian_speed_with_bounded_uncertainty_is_displayable() -> None:
    result = TrajectoryReconstructor._point_result(
        TrajectoryPoint(
            report_index=438,
            timestamp_sec=17.52,
            world_x=1.0,
            world_y=2.0,
            raw_speed_kmh=7.6,
            speed_confidence=0.72,
            speed_uncertainty_kmh=2.5,
            calibration_confidence=0.716667,
            contact_confidence=0.5202,
            tracking_confidence=1.0,
            occlusion_confidence=1.0,
        ),
        0,
        1.0,
        2.0,
        velocity=np.array([2.0, 0.0]),
        speed_kmh=7.6,
        acceleration=None,
        metrics=SpeedStabilityMetrics(
            speed_stability_score=0.39,
            speed_cv=0.33,
            max_speed_jump_kmh=3.0,
            speed_jump_p95_kmh=2.0,
            acceleration_p95_mps2=4.0,
            jerk_p95_mps3=5.0,
            stability_label="unstable_observation",
        ),
    )

    assert result["physics_confidence"] < 0.2
    assert result["physics_valid"] is True
    assert result["quality_label"] == "variable"
    assert result["rejection_reason"] is None
    assert result["confidence_rejection_reason"] is None


def test_pedestrian_speed_with_wide_rts_uncertainty_remains_displayable() -> None:
    result = TrajectoryReconstructor._point_result(
        TrajectoryPoint(
            report_index=24,
            timestamp_sec=0.96,
            world_x=1.0,
            world_y=2.0,
            raw_speed_kmh=9.6,
            speed_confidence=0.33,
            speed_uncertainty_kmh=12.9,
            calibration_confidence=0.65,
            contact_confidence=0.324,
            tracking_confidence=1.0,
            occlusion_confidence=1.0,
        ),
        0,
        1.0,
        2.0,
        velocity=np.array([2.6667, 0.0]),
        speed_kmh=9.6,
        acceleration=None,
        metrics=SpeedStabilityMetrics(
            speed_stability_score=0.27,
            speed_cv=0.92,
            max_speed_jump_kmh=1.7,
            speed_jump_p95_kmh=1.7,
            acceleration_p95_mps2=4.0,
            jerk_p95_mps3=5.0,
            stability_label="unstable_observation",
        ),
    )

    assert result["physics_confidence"] < 0.2
    assert result["physics_valid"] is True
    assert result["quality_label"] == "variable"
    assert result["speed_uncertainty_kmh"] == pytest.approx(18.705)
    assert result["confidence_rejection_reason"] is None


def test_reconstructed_pedestrian_speed_is_capped_to_display_range() -> None:
    result = TrajectoryReconstructor._point_result(
        TrajectoryPoint(
            report_index=31,
            timestamp_sec=1.24,
            world_x=1.0,
            world_y=2.0,
            raw_speed_kmh=24.0,
            speed_confidence=0.72,
            speed_uncertainty_kmh=6.0,
            calibration_confidence=0.65,
            contact_confidence=0.52,
            tracking_confidence=1.0,
            occlusion_confidence=1.0,
        ),
        0,
        1.0,
        2.0,
        velocity=np.array([6.6667, 0.0]),
        speed_kmh=24.0,
        acceleration=None,
        metrics=SpeedStabilityMetrics(
            speed_stability_score=0.42,
            speed_cv=0.2,
            max_speed_jump_kmh=2.0,
            speed_jump_p95_kmh=2.0,
            acceleration_p95_mps2=4.0,
            jerk_p95_mps3=5.0,
            stability_label="stable",
        ),
    )

    assert result["speed_kmh"] == 18.0
    assert result["physics_valid"] is True
    assert result["confidence_rejection_reason"] is None


def test_stable_reconstructed_vehicle_speed_keeps_low_physics_confidence_invalid() -> None:
    reconstructor = TrajectoryReconstructor()
    reports = []
    for frame_index in range(60):
        timestamp = frame_index / 25.0
        reports.append(
            {
                "frame_index": frame_index,
                "timestamp_sec": timestamp,
                "active_tracks": [
                    {
                        "tracker_id": 41,
                        "class_id": 2,
                        "class_name": "car",
                        "speed_kmh": 18.0,
                        "speed_confidence": 0.72,
                        "speed_uncertainty_kmh": 1.8,
                        "physics_valid": True,
                        "quality_label": "stable",
                        "ground_x_m": 5.0 * timestamp,
                        "ground_y_m": 0.0,
                        "calibration_confidence": 0.08,
                        "contact_confidence": 0.72,
                        "tracking_confidence": 0.85,
                        "occlusion_confidence": 0.9,
                    }
                ],
            }
        )

    updated = reconstructor.reconstruct_reports(reports)
    track = updated[-1]["active_tracks"][0]

    assert track["quality_label"] == "stable"
    assert track["physics_confidence"] < 0.2
    assert track["physics_valid"] is False
    assert track["confidence_rejection_reason"] == "dynamics_confidence"


def test_short_two_frame_pedestrian_track_gets_bootstrap_speed() -> None:
    reconstructor = TrajectoryReconstructor()
    reports = []
    for frame_index in (18, 19):
        timestamp = frame_index / 25.0
        reports.append(
            {
                "frame_index": frame_index,
                "timestamp_sec": timestamp,
                "active_tracks": [
                    {
                        "tracker_id": 17,
                        "class_id": 0,
                        "class_name": "person",
                        "speed_kmh": None,
                        "physics_valid": False,
                        "quality_label": "geometry_invalid",
                        "rejection_reason": "far_field_perspective_rejected",
                        "ground_x_m": 6.5 + (frame_index - 18) * 0.015,
                        "ground_y_m": 39.4,
                        "calibration_confidence": 0.72,
                        "contact_confidence": 0.55,
                        "tracking_confidence": 1.0,
                        "occlusion_confidence": 1.0,
                    }
                ],
            }
        )

    updated = reconstructor.reconstruct_reports(reports)

    for report in updated:
        track = report["active_tracks"][0]
        assert track["speed_kmh"] is not None
        assert track["physics_valid"] is True
        assert track["quality_label"] == "variable"
        assert track["stability_label"] == "short_track_bootstrap"
        assert track["reconstructed"] is True
        assert track["rejection_reason"] is None


def test_low_speed_stable_pedestrian_allows_absolute_uncertainty_gate() -> None:
    result = TrajectoryReconstructor._point_result(
        TrajectoryPoint(
            report_index=716,
            timestamp_sec=28.64,
            world_x=1.0,
            world_y=2.0,
            raw_speed_kmh=0.66,
            speed_confidence=0.72,
            speed_uncertainty_kmh=0.5,
            calibration_confidence=0.716667,
            contact_confidence=0.414894,
            tracking_confidence=1.0,
            occlusion_confidence=1.0,
            reconstructed=True,
        ),
        0,
        1.0,
        2.0,
        velocity=np.array([0.1833, 0.0]),
        speed_kmh=0.66,
        acceleration=None,
        metrics=SpeedStabilityMetrics(
            speed_stability_score=0.99,
            speed_cv=0.0,
            max_speed_jump_kmh=0.0,
            speed_jump_p95_kmh=0.0,
            acceleration_p95_mps2=0.0,
            jerk_p95_mps3=0.0,
            stability_label="stable",
        ),
    )

    assert result["physics_valid"] is True
    assert result["quality_label"] == "stable"
    assert result["confidence_rejection_reason"] is None


def test_reconstruction_keeps_reused_tracker_id_classes_separate() -> None:
    reconstructor = TrajectoryReconstructor()
    reports = []
    for frame_index in range(12):
        timestamp = frame_index / 25.0
        class_id = 1 if frame_index < 8 else 0
        reports.append(
            {
                "frame_index": frame_index,
                "timestamp_sec": timestamp,
                "active_tracks": [
                    {
                        "tracker_id": 20,
                        "class_id": class_id,
                        "class_name": "bicycle" if class_id == 1 else "person",
                        "speed_kmh": 1.8,
                        "speed_confidence": 0.72,
                        "speed_uncertainty_kmh": 0.5,
                        "physics_valid": class_id == 1,
                        "quality_label": "stable",
                        "ground_x_m": 13.0 + 0.012 * frame_index,
                        "ground_y_m": 39.0 + 0.016 * frame_index,
                        "calibration_confidence": 0.716667,
                        "contact_confidence": 0.20433 if class_id == 0 else 0.72,
                        "tracking_confidence": 1.0,
                        "occlusion_confidence": 1.0,
                    }
                ],
            }
        )

    updated = reconstructor.reconstruct_reports(reports)
    person_track = updated[-1]["active_tracks"][0]

    assert person_track["class_id"] == 0
    assert person_track["physics_valid"] is True
    assert person_track["confidence_rejection_reason"] is None


def test_reconstruction_marks_missing_short_gap_as_reconstructed() -> None:
    reconstructor = TrajectoryReconstructor()
    reports = []
    for frame_index in range(20):
        timestamp = frame_index / 10.0
        active_tracks = []
        if frame_index not in {9, 10}:
            active_tracks.append(
                {
                    "tracker_id": 13,
                    "class_id": 2,
                    "speed_kmh": 36.0,
                    "ground_x_m": 10.0 * timestamp,
                    "ground_y_m": 0.0,
                }
            )
        reports.append(
            {
                "frame_index": frame_index,
                "timestamp_sec": timestamp,
                "active_tracks": active_tracks,
            }
        )

    updated = reconstructor.reconstruct_reports(reports)

    gap_tracks = [
        track
        for frame_index in (9, 10)
        for track in updated[frame_index]["active_tracks"]
        if track["tracker_id"] == 13
    ]
    assert len(gap_tracks) == 2
    assert all(track["reconstructed"] is True for track in gap_tracks)
    assert all(track["speed_confidence"] is not None for track in gap_tracks)
    assert all(track["speed_uncertainty_kmh"] is not None for track in gap_tracks)
    assert updated[-1]["trajectory_diagnostics"]["reconstructed_ratio"] > 0.0
    assert updated[-1]["trajectory_diagnostics"]["track_fragmentation_count"] >= 1
    assert "low_confidence_ratio" in updated[-1]["trajectory_diagnostics"]
