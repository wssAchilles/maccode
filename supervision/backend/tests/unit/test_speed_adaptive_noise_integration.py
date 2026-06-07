from __future__ import annotations

import numpy as np
from domain.motion.router import MotionRouter
from domain.speed.estimator import SpeedEstimator
from domain.speed.view_transformer import ViewTransformer


def test_speed_estimator_records_adaptive_noise_diagnostics() -> None:
    estimator = SpeedEstimator(
        ViewTransformer(np.eye(3, dtype=np.float64)),
        position_rmse_m=0.05,
        timestamp_uncertainty_sec=0.01,
    )
    motion_profile = MotionRouter().route_class(2)

    for index in range(8):
        estimator.update(
            tracker_id=7,
            pixel_center=(float(index), 0.0),
            timestamp_sec=float(index),
            motion_profile=motion_profile,
            detection_confidence=0.95,
            measurement_confidence=0.95,
            pixel_sigma_px=0.05,
        )

    record = estimator.get_record(7)

    assert record is not None
    assert record.adaptive_measurement_noise_multiplier is not None
    assert record.innovation_nis is not None
    assert record.adaptive_measurement_noise_multiplier > 0.0
    assert record.position_covariance is not None
    assert len(record.position_covariance) == 2
    assert len(record.position_covariance[0]) == 2


def test_pedestrian_far_field_perspective_inflation_is_rejected() -> None:
    homography = np.array(
        [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, -0.035, 1.0]],
        dtype=np.float64,
    )
    estimator = SpeedEstimator(
        ViewTransformer(homography),
        position_rmse_m=0.05,
        timestamp_uncertainty_sec=0.01,
    )
    motion_profile = MotionRouter().route_class(0)

    for index, y in enumerate([0.0, 2.0, 4.0, 6.0, 8.0, 10.0, 12.0, 14.0, 16.0]):
        estimator.update(
            tracker_id=3,
            pixel_center=(0.0, y),
            timestamp_sec=float(index),
            motion_profile=motion_profile,
            detection_confidence=0.95,
            measurement_confidence=0.95,
            pixel_sigma_px=0.05,
            local_scale_percentile=min(0.99, 0.5 + index * 0.07),
        )

    record = estimator.get_record(3)

    assert record is not None
    assert record.speed_kmh is None
    assert record.physics_valid is False
    assert record.quality_label == "geometry_invalid"
    assert record.rejection_reason in {
        "perspective_speed_inflation",
        "pedestrian_physical_speed_gate",
    }
    assert record.perspective_speed_inflation_detected is True
    assert record.geometry_rejection_reason is not None
