from __future__ import annotations

import math

import numpy as np
import pytest
from domain.calibration.models import CalibrationPoint
from domain.calibration.service import CalibrationService
from domain.speed.estimator import SpeedEstimator
from domain.speed.filters import max_speed_filter, min_displacement_filter
from domain.speed.smoothing import exponential_smoothing, median_smoothing
from domain.speed.view_transformer import ViewTransformer


def square_points() -> list[CalibrationPoint]:
    return [
        CalibrationPoint(0, 0, 0, 0),
        CalibrationPoint(100, 0, 10, 0),
        CalibrationPoint(100, 100, 10, 10),
        CalibrationPoint(0, 100, 0, 10),
    ]


def test_calibration_rejects_less_than_four_points() -> None:
    service = CalibrationService()

    with pytest.raises(ValueError, match="at least 4"):
        service.validate_points(square_points()[:3])


def test_calibration_rejects_collinear_pixel_points() -> None:
    service = CalibrationService()
    points = [
        CalibrationPoint(0, 0, 0, 0),
        CalibrationPoint(10, 10, 1, 1),
        CalibrationPoint(20, 20, 2, 2),
        CalibrationPoint(30, 30, 3, 3),
    ]

    with pytest.raises(ValueError, match="collinear"):
        service.validate_points(points)


def test_homography_maps_pixel_square_to_world_square() -> None:
    service = CalibrationService()
    result = service.compute_homography(square_points())
    transformer = ViewTransformer(result.homography_matrix)

    assert result.reprojection_rmse < 1e-6
    assert transformer.transform_point(50, 50) == pytest.approx((5.0, 5.0))


def test_speed_estimator_returns_stable_uniform_speed() -> None:
    transformer = ViewTransformer(np.array([[0.1, 0, 0], [0, 0.1, 0], [0, 0, 1]], dtype=float))
    estimator = SpeedEstimator(
        view_transformer=transformer,
        smoothing_window=3,
        min_displacement_m=0.01,
        max_speed_kmh=200.0,
    )

    assert estimator.update(1, (0, 0), timestamp_sec=0.0) is None
    assert estimator.update(1, (10, 0), timestamp_sec=1.0) == pytest.approx(3.6)
    assert estimator.update(1, (20, 0), timestamp_sec=2.0) == pytest.approx(3.6)


def test_speed_estimator_filters_static_and_unrealistic_motion() -> None:
    transformer = ViewTransformer(np.eye(3))
    estimator = SpeedEstimator(transformer, min_displacement_m=0.5, max_speed_kmh=10.0)

    assert estimator.update(1, (0, 0), timestamp_sec=0.0) is None
    assert estimator.update(1, (0.1, 0), timestamp_sec=1.0) == pytest.approx(0.0)
    assert estimator.update(1, (100, 0), timestamp_sec=2.0) is None


def test_smoothing_and_filters_are_deterministic() -> None:
    assert median_smoothing([10, 90, 12], window_size=3) == pytest.approx(12.0)
    assert exponential_smoothing([10, 20, 30], alpha=0.5) == pytest.approx(22.5)
    assert min_displacement_filter(0.05, threshold=0.1) == 0.0
    assert max_speed_filter(250.0, max_speed=200.0) is None
    valid_speed = max_speed_filter(88.0, max_speed=200.0)
    assert valid_speed is not None
    assert math.isclose(valid_speed, 88.0)
