from __future__ import annotations

import math

import numpy as np
import pytest
from domain.calibration.models import CalibrationPoint
from domain.calibration.service import CalibrationService
from domain.speed.estimator import SpeedEstimator
from domain.speed.filters import max_speed_filter, min_displacement_filter
from domain.speed.geometry_diagnostics import TrackGeometryDiagnosticBuilder
from domain.speed.ground_contact import GroundContactCorrector
from domain.speed.models import TrackHistory
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
    assert result.pixel_to_world_rmse_m < 1e-6
    assert result.world_to_pixel_rmse_px < 1e-6
    assert transformer.transform_point(50, 50) == pytest.approx((5.0, 5.0))


def test_homography_grid_carries_trust_and_is_clipped_to_world_polygon() -> None:
    service = CalibrationService()
    result = service.compute_homography(square_points())

    grid = service.build_homography_grid(
        result,
        frame_width=100,
        frame_height=100,
        world_width_m=10,
        world_length_m=10,
        spacing_m=5,
        calibration_source="video_manual_preset",
        calibration_trusted=True,
        road_plane_polygon_world=[(2.0, 2.0), (8.0, 2.0), (8.0, 8.0), (2.0, 8.0)],
        validation_max_error_px=3.0,
    )

    assert grid.calibration_trusted is True
    assert grid.calibration_source == "video_manual_preset"
    assert grid.pixel_rmse_px == pytest.approx(0.0)
    assert grid.validation_max_error_px == pytest.approx(3.0)
    assert grid.lines
    for line in grid.lines:
        assert 2.0 <= line.world_start[0] <= 8.0
        assert 2.0 <= line.world_start[1] <= 8.0
        assert 2.0 <= line.world_end[0] <= 8.0
        assert 2.0 <= line.world_end[1] <= 8.0


def test_metric_plane_set_selects_trusted_plane_and_rejects_ambiguous_edges() -> None:
    service = CalibrationService()
    plane_set = service.build_metric_plane_set(
        metric_planes=[
            {
                "plane_id": "road",
                "plane_kind": "road",
                "trusted": True,
                "pixel_polygon": [[0, 0], [60, 0], [60, 100], [0, 100]],
                "world_polygon": [[0, 0], [6, 0], [6, 10], [0, 10]],
                "control_points": [
                    {"pixel_x": 0, "pixel_y": 0, "world_x": 0, "world_y": 0},
                    {"pixel_x": 60, "pixel_y": 0, "world_x": 6, "world_y": 0},
                    {"pixel_x": 60, "pixel_y": 100, "world_x": 6, "world_y": 10},
                    {"pixel_x": 0, "pixel_y": 100, "world_x": 0, "world_y": 10},
                ],
            },
            {
                "plane_id": "sidewalk",
                "plane_kind": "sidewalk",
                "trusted": True,
                "pixel_polygon": [[50, 0], [90, 0], [90, 100], [50, 100]],
                "world_polygon": [[0, 0], [4, 0], [4, 10], [0, 10]],
                "control_points": [
                    {"pixel_x": 50, "pixel_y": 0, "world_x": 0, "world_y": 0},
                    {"pixel_x": 90, "pixel_y": 0, "world_x": 4, "world_y": 0},
                    {"pixel_x": 90, "pixel_y": 100, "world_x": 4, "world_y": 10},
                    {"pixel_x": 50, "pixel_y": 100, "world_x": 0, "world_y": 10},
                ],
            },
        ],
    )

    assert plane_set.select((25, 25)).plane is not None
    assert plane_set.select((25, 25)).plane.plane_id == "road"
    assert plane_set.select((75, 25)).plane is not None
    assert plane_set.select((75, 25)).plane.plane_id == "sidewalk"
    assert plane_set.select((55, 25)).reason == "plane_transition_geometry_invalid"
    assert plane_set.select((95, 25)).reason == "plane_unresolved"


def test_single_plane_legacy_calibration_can_fallback_to_default_road_plane() -> None:
    service = CalibrationService()
    homography = service.compute_homography(square_points())

    plane_set = service.build_metric_plane_set(
        default_control_points=square_points(),
        default_homography=homography,
        default_trusted=True,
    )

    selection = plane_set.select((150, 150))

    assert selection.status == "default"
    assert selection.plane is not None
    assert selection.plane.plane_id == "road"


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


def test_weighted_regression_downweights_far_field_perspective_noise() -> None:
    history = TrackHistory(1)
    for timestamp in [0.0, 0.2, 0.4, 0.6]:
        history.add_position(
            (timestamp * 1.2, 0.0),
            timestamp,
            measurement_confidence=1.0,
            position_sigma_m=0.03,
            local_scale_percentile=0.3,
        )
    for timestamp, noisy_x in [(0.8, 1.9), (1.0, 2.3)]:
        history.add_position(
            (noisy_x, 0.0),
            timestamp,
            measurement_confidence=0.35,
            position_sigma_m=1.8,
            local_scale_percentile=0.97,
        )

    regression = SpeedEstimator._fit_window(history, regression_window_sec=1.2)

    assert regression is not None
    assert regression.speed_kmh == pytest.approx(1.2 * 3.6, abs=1.5)


def test_metric_covariance_projects_contact_pixel_covariance_through_homography() -> None:
    transformer = ViewTransformer(np.array([[0.2, 0, 0], [0, 0.2, 0], [0, 0, 1]], dtype=float))
    estimator = SpeedEstimator(transformer)
    local_uncertainty = transformer.local_position_uncertainty(10, 10, pixel_sigma=1.0)

    covariance = estimator._measurement_covariance(  # noqa: SLF001
        (10, 10),
        local_uncertainty,
        scalar_measurement_noise=0.001,
        pixel_covariance_px=[[9.0, 0.0], [0.0, 25.0]],
    )

    assert covariance[0, 0] > local_uncertainty.covariance[0, 0]
    assert covariance[1, 1] > covariance[0, 0]


def test_bbox_contact_covariance_marks_person_footpoint_as_noisier_vertically() -> None:
    contact = GroundContactCorrector().correct(
        tracker_id=1,
        class_id=0,
        xyxy=[10.0, 5.0, 30.0, 85.0],
        timestamp_sec=0.0,
    )

    assert contact.pixel_covariance is not None
    assert contact.pixel_covariance[1][1] > contact.pixel_covariance[0][0]


def test_track_geometry_diagnostics_exports_perspective_coupled_drift() -> None:
    reports = []
    for index, (speed, scale, height) in enumerate(
        [(5.0, 1.0, 80.0), (8.0, 2.0, 50.0), (12.0, 3.0, 32.0), (15.0, 4.0, 24.0)],
        start=1,
    ):
        reports.append(
            {
                "frame_index": index,
                "timestamp_sec": float(index),
                "active_tracks": [
                    {
                        "tracker_id": 13,
                        "class_name": "person",
                        "xyxy": [10.0, 10.0, 30.0, 10.0 + height],
                        "ground_x_m": float(index),
                        "ground_y_m": 0.0,
                        "speed_kmh": speed,
                        "physics_valid": True,
                        "local_scale_factor": scale,
                        "speed_geometry_diagnostics": {
                            "bbox_height_px": height,
                            "raw_bbox_foot": [20.0, 10.0 + height],
                            "fused_foot": [20.0, 10.0 + height],
                            "contact_covariance_px": [[1.0, 0.0], [0.0, 2.0]],
                            "plane_id": "sidewalk",
                            "plane_status": "selected",
                        },
                    }
                ],
            }
        )

    diagnostic = TrackGeometryDiagnosticBuilder().build(reports, tracker_id=13)

    assert diagnostic.rows[0]["plane_id"] == "sidewalk"
    assert diagnostic.metrics["sample_count"] == 4
    assert diagnostic.metrics["speed_cv"] is not None
    assert diagnostic.metrics["perspective_coupled_speed_drift"] is True


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
