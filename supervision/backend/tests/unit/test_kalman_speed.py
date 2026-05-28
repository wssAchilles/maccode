from __future__ import annotations

import pytest
from domain.speed.kalman import KalmanFilter2D, kalman_config_for_motion_profile


def test_kalman_filter_converges_on_uniform_vehicle_speed() -> None:
    config = kalman_config_for_motion_profile("low")
    tracker = KalmanFilter2D(config)

    states = [
        tracker.update((float(index), 0.0), timestamp_sec=float(index))
        for index in range(8)
    ]

    assert states[-1].speed_kmh == pytest.approx(3.6, abs=0.35)
    assert states[-1].velocity_mps[0] == pytest.approx(1.0, abs=0.1)
    assert states[-1].speed_confidence > 0.75


def test_high_process_noise_responds_faster_than_vehicle_profile_to_turning_motion() -> None:
    vehicle_filter = KalmanFilter2D(kalman_config_for_motion_profile("low"))
    pedestrian_filter = KalmanFilter2D(kalman_config_for_motion_profile("high"))
    positions = [(0.0, 0.0), (1.0, 0.0), (2.0, 0.0), (2.0, 2.0), (2.0, 4.0)]

    vehicle_states = [
        vehicle_filter.update(position, timestamp_sec=float(index))
        for index, position in enumerate(positions)
    ]
    pedestrian_states = [
        pedestrian_filter.update(position, timestamp_sec=float(index))
        for index, position in enumerate(positions)
    ]

    assert pedestrian_states[-1].velocity_mps[1] > vehicle_states[-1].velocity_mps[1]
    assert pedestrian_states[-1].position[1] > vehicle_states[-1].position[1]


def test_kalman_filter_keeps_static_target_near_zero_speed() -> None:
    tracker = KalmanFilter2D(kalman_config_for_motion_profile("low"))

    states = [
        tracker.update((10.0, 5.0), timestamp_sec=float(index))
        for index in range(6)
    ]

    assert states[-1].speed_kmh == pytest.approx(0.0, abs=0.05)
