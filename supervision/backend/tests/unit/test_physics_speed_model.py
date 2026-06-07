from __future__ import annotations

import random

import numpy as np
import pytest
from domain.motion.router import MotionRouter
from domain.speed.estimator import SpeedEstimator
from domain.speed.kalman import (
    ConstantAccelerationKalmanFilter2D,
    KalmanConfig,
    KalmanFilter2D,
    KalmanMeasurementPrediction,
)
from domain.speed.uncertainty import estimate_speed_uncertainty
from domain.speed.view_transformer import ViewTransformer


def _meter_transformer() -> ViewTransformer:
    return ViewTransformer(np.eye(3))


def test_person_walking_speed_uses_physical_window_model() -> None:
    estimator = SpeedEstimator(_meter_transformer(), position_rmse_m=0.08)
    profile = MotionRouter().route_class(0)

    latest_speed = None
    for frame_index in range(45):
        timestamp = frame_index / 30.0
        latest_speed = estimator.update(
            7,
            (1.4 * timestamp, 0.0),
            timestamp_sec=timestamp,
            motion_profile=profile,
            detection_confidence=0.9,
        )

    record = estimator.get_record(7)
    assert latest_speed == pytest.approx(5.04, abs=0.7)
    assert record is not None
    assert record.physics_valid is True
    assert record.quality_label == "stable"
    assert record.speed_uncertainty_kmh is not None
    assert record.speed_uncertainty_kmh < 8.0


def test_person_single_frame_jump_is_rejected_as_unphysical() -> None:
    estimator = SpeedEstimator(_meter_transformer(), position_rmse_m=0.08)
    profile = MotionRouter().route_class(0)

    for frame_index in range(30):
        timestamp = frame_index / 30.0
        estimator.update(
            8,
            (1.2 * timestamp, 0.0),
            timestamp_sec=timestamp,
            motion_profile=profile,
            detection_confidence=0.9,
        )

    rejected_speed = estimator.update(
        8,
        (50.0, 0.0),
        timestamp_sec=31 / 30.0,
        motion_profile=profile,
        detection_confidence=0.9,
    )
    record = estimator.get_record(8)

    assert rejected_speed is None
    assert record is not None
    assert record.physics_valid is False
    assert record.quality_label == "rejected"
    assert record.speed_kmh is None
    assert record.rejection_reason == "pedestrian_physical_speed_gate"


def test_car_uniform_speed_is_stable_and_physics_valid() -> None:
    estimator = SpeedEstimator(_meter_transformer(), position_rmse_m=0.3)
    profile = MotionRouter().route_class(2)
    target_speed_mps = 50.0 / 3.6

    latest_speed = None
    for frame_index in range(60):
        timestamp = frame_index / 30.0
        latest_speed = estimator.update(
            42,
            (target_speed_mps * timestamp, 0.0),
            timestamp_sec=timestamp,
            motion_profile=profile,
            detection_confidence=0.92,
        )

    record = estimator.get_record(42)
    assert latest_speed == pytest.approx(50.0, abs=3.0)
    assert record is not None
    assert record.physics_valid is True
    assert record.speed_confidence is not None
    assert record.speed_confidence >= profile.confidence_floor


def test_uniform_vehicle_speed_display_resists_detection_jitter() -> None:
    estimator = SpeedEstimator(_meter_transformer(), position_rmse_m=0.2)
    profile = MotionRouter().route_class(2)
    target_speed_mps = 36.0 / 3.6
    displayed_speeds: list[float] = []

    for frame_index in range(90):
        timestamp = frame_index / 30.0
        jitter = 0.45 if frame_index % 2 == 0 else -0.45
        speed = estimator.update(
            43,
            (target_speed_mps * timestamp + jitter, 0.12 * jitter),
            timestamp_sec=timestamp,
            motion_profile=profile,
            detection_confidence=0.92,
        )
        if speed is not None:
            displayed_speeds.append(speed)

    assert displayed_speeds
    assert displayed_speeds[-1] == pytest.approx(36.0, abs=3.0)
    assert max(
        abs(current - previous)
        for previous, current in zip(displayed_speeds, displayed_speeds[1:], strict=False)
    ) <= 1.5


def test_uniform_pedestrian_speed_display_resists_random_footpoint_jitter() -> None:
    estimator = SpeedEstimator(_meter_transformer(), position_rmse_m=0.1)
    profile = MotionRouter().route_class(0)
    rng = random.Random(7)
    target_speed_mps = 5.0 / 3.6
    displayed_speeds: list[float] = []

    for frame_index in range(120):
        timestamp = frame_index / 30.0
        footpoint_jitter_x = rng.uniform(-0.4, 0.4)
        footpoint_jitter_y = rng.uniform(-0.08, 0.08)
        speed = estimator.update(
            44,
            (
                target_speed_mps * timestamp + footpoint_jitter_x,
                footpoint_jitter_y,
            ),
            timestamp_sec=timestamp,
            motion_profile=profile,
            detection_confidence=0.9,
        )
        if speed is not None:
            displayed_speeds.append(speed)

    assert displayed_speeds
    assert displayed_speeds[-1] == pytest.approx(5.0, abs=0.8)
    assert max(
        abs(current - previous)
        for previous, current in zip(displayed_speeds, displayed_speeds[1:], strict=False)
    ) <= 0.6


def test_auxiliary_bev_velocity_stabilizes_jittered_ground_observations() -> None:
    estimator = SpeedEstimator(_meter_transformer(), position_rmse_m=0.12)
    profile = MotionRouter().route_class(0)
    rng = random.Random(11)
    target_speed_mps = 5.5 / 3.6
    displayed_speeds: list[float] = []

    for frame_index in range(120):
        timestamp = frame_index / 30.0
        jitter_x = rng.uniform(-0.7, 0.7)
        jitter_y = rng.uniform(-0.12, 0.12)
        speed = estimator.update(
            45,
            (target_speed_mps * timestamp + jitter_x, jitter_y),
            timestamp_sec=timestamp,
            motion_profile=profile,
            detection_confidence=0.85,
            auxiliary_velocity_mps=(target_speed_mps, 0.0),
            auxiliary_confidence=0.85,
        )
        if speed is not None:
            displayed_speeds.append(speed)

    assert displayed_speeds
    assert displayed_speeds[-1] == pytest.approx(5.5, abs=0.75)
    assert max(
        abs(current - previous)
        for previous, current in zip(displayed_speeds, displayed_speeds[1:], strict=False)
    ) <= 0.6


def test_inconsistent_auxiliary_velocity_is_rejected() -> None:
    estimator = SpeedEstimator(_meter_transformer(), position_rmse_m=0.12)
    profile = MotionRouter().route_class(2)
    target_speed_mps = 10.0
    displayed_speeds: list[float] = []

    for frame_index in range(90):
        timestamp = frame_index / 30.0
        speed = estimator.update(
            46,
            (target_speed_mps * timestamp, 0.0),
            timestamp_sec=timestamp,
            motion_profile=profile,
            detection_confidence=0.9,
            auxiliary_velocity_mps=(0.0, target_speed_mps * 4.0),
            auxiliary_confidence=0.99,
        )
        if speed is not None:
            displayed_speeds.append(speed)

    assert displayed_speeds
    assert displayed_speeds[-1] == pytest.approx(target_speed_mps * 3.6, abs=3.0)


def test_view_transformer_reports_larger_far_field_position_sigma() -> None:
    transformer = ViewTransformer(
        np.array(
            [
                [0.03, 0.0, 0.0],
                [0.0, 0.03, 0.0],
                [0.0, -0.0015, 1.0],
            ],
            dtype=float,
        )
    )

    near = transformer.local_position_uncertainty(100.0, 100.0, pixel_sigma=1.0)
    far = transformer.local_position_uncertainty(100.0, 500.0, pixel_sigma=1.0)

    assert far.position_sigma_m > near.position_sigma_m
    assert far.local_scale_factor > near.local_scale_factor
    assert far.covariance.shape == (2, 2)


def test_low_measurement_confidence_has_less_effect_on_adaptive_kalman_state() -> None:
    low_quality = KalmanFilter2D(KalmanConfig(process_noise=0.5, measurement_noise=0.1))
    high_quality = KalmanFilter2D(KalmanConfig(process_noise=0.5, measurement_noise=0.1))

    for frame_index in range(12):
        timestamp = frame_index / 10.0
        low_quality.update((timestamp, 0.0), timestamp, measurement_noise=0.1)
        high_quality.update((timestamp, 0.0), timestamp, measurement_noise=0.1)

    low_quality.update((12.0, 0.0), 1.3, measurement_noise=50.0)
    high_quality.update((12.0, 0.0), 1.3, measurement_noise=0.05)

    assert high_quality.state is not None
    assert low_quality.state is not None
    assert high_quality.state.position[0] > low_quality.state.position[0]


def test_constant_acceleration_kalman_tracks_startup_acceleration() -> None:
    tracker = ConstantAccelerationKalmanFilter2D(
        KalmanConfig(process_noise=0.8, measurement_noise=0.05),
    )

    states = [
        tracker.update((0.5 * 2.0 * timestamp**2, 0.0), timestamp_sec=timestamp)
        for timestamp in [index / 5.0 for index in range(1, 16)]
    ]

    assert states[-1].velocity_mps[0] == pytest.approx(2.0 * 3.0, abs=1.0)
    assert states[-1].acceleration_mps2 is not None
    assert states[-1].acceleration_mps2 > 0.5


def test_robust_window_regression_ignores_single_local_outlier() -> None:
    estimator = SpeedEstimator(_meter_transformer(), position_rmse_m=0.08)
    profile = MotionRouter().route_class(2)
    target_speed_mps = 36.0 / 3.6
    speeds: list[float] = []

    for frame_index in range(90):
        timestamp = frame_index / 30.0
        outlier = 6.0 if frame_index == 72 else 0.0
        speed = estimator.update(
            72,
            (target_speed_mps * timestamp + outlier, 0.0),
            timestamp_sec=timestamp,
            motion_profile=profile,
            detection_confidence=0.95,
            measurement_confidence=0.95 if outlier == 0.0 else 0.25,
        )
        if speed is not None:
            speeds.append(speed)

    assert speeds
    assert speeds[-1] == pytest.approx(36.0, abs=3.0)


def test_vehicle_id_switch_jump_does_not_pollute_speed_record() -> None:
    estimator = SpeedEstimator(_meter_transformer(), position_rmse_m=0.3)
    profile = MotionRouter().route_class(2)

    for frame_index in range(45):
        timestamp = frame_index / 30.0
        estimator.update(
            99,
            (8.0 * timestamp, 0.0),
            timestamp_sec=timestamp,
            motion_profile=profile,
            detection_confidence=0.9,
        )

    assert estimator.get_record(99) is not None
    rejected_speed = estimator.update(
        99,
        (400.0, 300.0),
        timestamp_sec=46 / 30.0,
        motion_profile=profile,
        detection_confidence=0.9,
    )
    record = estimator.get_record(99)

    assert rejected_speed is None
    assert record is not None
    assert record.physics_valid is False
    assert record.speed_kmh is None
    assert record.rejection_reason == "speed_gate"


def test_kalman_predict_measurement_returns_mahalanobis_distance() -> None:
    kalman = KalmanFilter2D(
        KalmanConfig(
            process_noise=0.01,
            measurement_noise=0.05,
            initial_position_variance=0.05,
            initial_velocity_variance=0.05,
        ),
    )
    kalman.update((0.0, 0.0), 0.0)
    kalman.update((1.0, 0.0), 1.0)

    normal = kalman.predict_measurement((2.0, 0.0), 2.0)
    jump = kalman.predict_measurement((12.0, 0.0), 2.0)

    assert normal.mahalanobis_d2 < 9.21
    assert jump.mahalanobis_d2 > 9.21
    assert jump.innovation_covariance.shape == (2, 2)


def test_vehicle_id_switch_under_speed_gate_is_rejected_by_mahalanobis_gate() -> None:
    estimator = SpeedEstimator(_meter_transformer(), position_rmse_m=0.3)
    profile = MotionRouter().route_class(2)

    for frame_index in range(45):
        timestamp = frame_index / 30.0
        estimator.update(
            100,
            (8.0 * timestamp, 0.0),
            timestamp_sec=timestamp,
            motion_profile=profile,
            detection_confidence=0.9,
        )

    rejected_speed = estimator.update(
        100,
        (28.0, 0.0),
        timestamp_sec=2.0,
        motion_profile=profile,
        detection_confidence=0.9,
    )
    record = estimator.get_record(100)

    assert rejected_speed is None
    assert record is not None
    assert record.physics_valid is False
    assert record.speed_kmh is None
    assert record.rejection_reason == "mahalanobis_gate"


def test_pinv_mahalanobis_path_uses_stricter_gate(monkeypatch: pytest.MonkeyPatch) -> None:
    estimator = SpeedEstimator(_meter_transformer(), position_rmse_m=0.3)
    profile = MotionRouter().route_class(2)
    estimator.update(
        101,
        (0.0, 0.0),
        timestamp_sec=0.0,
        motion_profile=profile,
        detection_confidence=0.9,
    )
    kalman_filter = estimator._kalman_filters[101]

    def pinv_prediction(
        position: tuple[float, float],
        timestamp_sec: float,
    ) -> KalmanMeasurementPrediction:
        return KalmanMeasurementPrediction(
            predicted_position=position,
            innovation=np.array([[2.0], [0.0]], dtype=np.float64),
            innovation_covariance=np.eye(2, dtype=np.float64),
            mahalanobis_d2=7.0,
            covariance_solver="pinv",
        )

    monkeypatch.setattr(kalman_filter, "predict_measurement", pinv_prediction)

    rejected_speed = estimator.update(
        101,
        (1.0, 0.0),
        timestamp_sec=1.0,
        motion_profile=profile,
        detection_confidence=0.9,
    )
    record = estimator.get_record(101)

    assert rejected_speed is None
    assert record is not None
    assert record.rejection_reason == "mahalanobis_gate"


def test_uncertainty_caps_unphysical_error_band() -> None:
    uncertainty = estimate_speed_uncertainty(
        displacement_m=0.04,
        delta_t_sec=1 / 30,
        position_rmse_m=2.0,
        timestamp_uncertainty_sec=1 / 30,
        uncertainty_cap_kmh=18.0,
    )

    assert uncertainty.speed_uncertainty_kmh <= 18.0
    assert uncertainty.speed_confidence < 0.2
    assert uncertainty.was_capped is True
