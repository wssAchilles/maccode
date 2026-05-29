from __future__ import annotations

import numpy as np
import pytest
from domain.motion.router import MotionRouter
from domain.speed.estimator import SpeedEstimator
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
    assert record.rejection_reason == "speed_gate"


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
