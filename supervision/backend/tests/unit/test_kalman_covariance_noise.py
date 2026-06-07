from __future__ import annotations

import numpy as np

from domain.speed.kalman import KalmanFilter2D, kalman_config_for_motion_profile


def test_anisotropic_measurement_covariance_reduces_matching_axis_nis() -> None:
    low_y_noise = KalmanFilter2D(kalman_config_for_motion_profile("low"))
    high_y_noise = KalmanFilter2D(kalman_config_for_motion_profile("low"))
    for index in range(4):
        position = (float(index), 0.0)
        low_y_noise.update(position, float(index), measurement_noise=0.05)
        high_y_noise.update(position, float(index), measurement_noise=0.05)

    low_prediction = low_y_noise.predict_measurement(
        (4.0, 5.0),
        4.0,
        measurement_noise=[[0.05, 0.0], [0.0, 0.05]],
    )
    high_prediction = high_y_noise.predict_measurement(
        (4.0, 5.0),
        4.0,
        measurement_noise=[[0.05, 0.0], [0.0, 25.0]],
    )

    assert high_prediction.mahalanobis_d2 < low_prediction.mahalanobis_d2
    assert high_prediction.innovation_covariance[1, 1] > low_prediction.innovation_covariance[1, 1]


def test_numpy_measurement_covariance_updates_filter() -> None:
    tracker = KalmanFilter2D(kalman_config_for_motion_profile("low"))
    tracker.update((0.0, 0.0), 0.0)

    state = tracker.update(
        (1.0, 0.0),
        1.0,
        measurement_noise=np.array([[0.1, 0.0], [0.0, 2.0]], dtype=np.float64),
    )

    assert state.position[0] > 0.0
