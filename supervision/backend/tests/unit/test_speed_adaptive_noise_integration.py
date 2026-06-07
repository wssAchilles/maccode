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
