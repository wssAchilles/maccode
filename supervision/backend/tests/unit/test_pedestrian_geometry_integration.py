from __future__ import annotations

import numpy as np
from domain.motion.router import MotionRouter
from domain.speed.estimator import SpeedEstimator
from domain.speed.view_transformer import ViewTransformer


def test_pedestrian_far_field_scale_drift_suppresses_moderate_speed() -> None:
    estimator = SpeedEstimator(
        ViewTransformer(np.eye(3, dtype=np.float64)),
        position_rmse_m=0.05,
        timestamp_uncertainty_sec=0.02,
    )
    profile = MotionRouter().route_class(0)
    y_positions = [
        0.0,
        0.7,
        1.5,
        2.4,
        3.4,
        4.5,
        5.7,
        7.0,
        8.4,
        9.9,
        11.5,
        13.2,
        15.0,
        16.9,
    ]

    for index, y in enumerate(y_positions):
        bbox_height = 96.0 - index * 5.0
        estimator.update(
            tracker_id=13,
            pixel_center=(100.0, y),
            timestamp_sec=float(index) * 0.25,
            motion_profile=profile,
            detection_confidence=0.95,
            measurement_confidence=0.95,
            pixel_sigma_px=0.05,
            measurement_source="bbox_ground_contact",
            local_scale_percentile=min(0.95, 0.30 + index * 0.07),
            bbox_xyxy=[80.0, y - bbox_height, 120.0, y],
            bbox_height_px=bbox_height,
        )

    record = estimator.get_record(13)

    assert record is not None
    assert record.speed_kmh is None
    assert record.physics_valid is False
    assert record.quality_label == "geometry_invalid"
    assert record.rejection_reason == "pedestrian_perspective_scale_drift"
    assert record.pedestrian_scale_drift_detected is True
    assert record.speed_inverse_height_correlation is not None
    assert record.pedestrian_geometry_model_reference == (
        "pedestrian_head_foot_scale_drift_v1"
    )


def test_pedestrian_far_field_over_18_kmh_is_not_stable() -> None:
    estimator = SpeedEstimator(ViewTransformer(np.eye(3, dtype=np.float64)))
    profile = MotionRouter().route_class(0)

    for index, y in enumerate([0.0, 1.5, 3.0, 4.5, 6.0, 7.5, 9.0, 10.5]):
        bbox_height = 90.0 - index * 5.0
        estimator.update(
            tracker_id=9,
            pixel_center=(30.0, y),
            timestamp_sec=float(index) * 0.25,
            motion_profile=profile,
            local_scale_percentile=0.86,
            bbox_xyxy=[20.0, y - bbox_height, 40.0, y],
            bbox_height_px=bbox_height,
        )

    record = estimator.get_record(9)

    assert record is not None
    assert record.speed_kmh is None
    assert record.physics_valid is False
    assert record.rejection_reason in {
        "pedestrian_perspective_scale_drift",
        "pedestrian_speed_outlier",
        "pedestrian_physical_speed_gate",
    }


def test_vehicle_does_not_use_pedestrian_scale_drift_strong_rejection() -> None:
    estimator = SpeedEstimator(ViewTransformer(np.eye(3, dtype=np.float64)))
    profile = MotionRouter().route_class(2)

    for index, y in enumerate([0.0, 4.0, 8.5, 13.5, 19.0, 25.0, 31.5]):
        bbox_height = 96.0 - index * 8.0
        estimator.update(
            tracker_id=7,
            pixel_center=(100.0, y),
            timestamp_sec=float(index),
            motion_profile=profile,
            local_scale_percentile=0.90,
            bbox_xyxy=[80.0, y - bbox_height, 120.0, y],
            bbox_height_px=bbox_height,
        )

    record = estimator.get_record(7)

    assert record is not None
    assert record.rejection_reason != "pedestrian_perspective_scale_drift"
