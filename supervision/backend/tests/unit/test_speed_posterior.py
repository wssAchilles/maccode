from __future__ import annotations

import numpy as np
from domain.calibration.models import HomographyResult
from domain.speed.models import SpeedRecord
from domain.speed.posterior import SpeedPosteriorAnalyzer


def _homography() -> HomographyResult:
    return HomographyResult(
        homography_matrix=np.eye(3, dtype=np.float64),
        reprojection_rmse=0.1,
        pixel_to_world_rmse_m=0.1,
        world_to_pixel_rmse_px=1.0,
        inlier_count=8,
        condition_number=100.0,
        inlier_mask=[True] * 8,
        calibration_quality="excellent",
    )


def _record(
    *,
    speed_kmh: float = 40.0,
    speed_uncertainty_kmh: float = 2.0,
    position_covariance: list[list[float]] | None = None,
) -> SpeedRecord:
    return SpeedRecord(
        tracker_id=1,
        speed_kmh=speed_kmh,
        timestamp_sec=1.0,
        world_x=0.0,
        world_y=0.0,
        speed_uncertainty_kmh=speed_uncertainty_kmh,
        position_covariance=position_covariance
        or [[0.01, 0.0], [0.0, 0.01]],
        velocity_x_mps=speed_kmh / 3.6,
        velocity_y_mps=0.0,
        physics_valid=True,
    )


def _width(summary: object) -> float:
    return float(summary.p95_kmh - summary.p05_kmh)


def test_joint_speed_posterior_is_reproducible() -> None:
    analyzer = SpeedPosteriorAnalyzer()

    left = analyzer.analyze(
        _record(),
        _homography(),
        timestamp_uncertainty_sec=0.02,
        sample_count=96,
        random_seed=7,
    )
    right = analyzer.analyze(
        _record(),
        _homography(),
        timestamp_uncertainty_sec=0.02,
        sample_count=96,
        random_seed=7,
    )

    assert left.to_dict() == right.to_dict()
    assert left.model_reference == "joint_speed_uncertainty_posterior_v1"


def test_larger_speed_uncertainty_widens_joint_posterior() -> None:
    analyzer = SpeedPosteriorAnalyzer()

    narrow = analyzer.analyze(
        _record(speed_uncertainty_kmh=1.0),
        _homography(),
        timestamp_uncertainty_sec=0.02,
        random_seed=11,
    )
    wide = analyzer.analyze(
        _record(speed_uncertainty_kmh=8.0),
        _homography(),
        timestamp_uncertainty_sec=0.02,
        random_seed=11,
    )

    assert _width(wide) > _width(narrow)


def test_larger_position_covariance_widens_joint_posterior() -> None:
    analyzer = SpeedPosteriorAnalyzer()

    narrow = analyzer.analyze(
        _record(position_covariance=[[0.01, 0.0], [0.0, 0.01]]),
        _homography(),
        timestamp_uncertainty_sec=0.02,
        random_seed=13,
    )
    wide = analyzer.analyze(
        _record(position_covariance=[[2.0, 0.0], [0.0, 2.0]]),
        _homography(),
        timestamp_uncertainty_sec=0.02,
        random_seed=13,
    )

    assert _width(wide) > _width(narrow)


def test_zero_speed_joint_posterior_is_not_negative() -> None:
    posterior = SpeedPosteriorAnalyzer().analyze(
        _record(speed_kmh=0.0, speed_uncertainty_kmh=3.0),
        _homography(),
        timestamp_uncertainty_sec=0.02,
        random_seed=17,
    )

    assert posterior.mean_kmh >= 0.0
    assert posterior.p05_kmh >= 0.0
    assert posterior.p95_kmh >= 0.0


def test_joint_speed_posterior_reports_sources() -> None:
    posterior = SpeedPosteriorAnalyzer().analyze(
        _record(),
        _homography(),
        timestamp_uncertainty_sec=0.02,
        random_seed=19,
    )

    assert set(posterior.sources) >= {
        "calibration_scale",
        "speed_uncertainty",
        "position_covariance",
        "timestamp_uncertainty",
    }
