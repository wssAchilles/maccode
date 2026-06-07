from __future__ import annotations

import random

import pytest
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
