from __future__ import annotations

import numpy as np
from domain.calibration.models import HomographyResult
from domain.calibration.monte_carlo import CalibrationMonteCarloAnalyzer


def _homography() -> HomographyResult:
    return HomographyResult(
        homography_matrix=np.array(
            [[0.1, 0.0, 0.0], [0.0, 0.1, 0.0], [0.0, 0.001, 1.0]],
            dtype=np.float64,
        ),
        reprojection_rmse=0.1,
        pixel_to_world_rmse_m=0.1,
        world_to_pixel_rmse_px=1.0,
        inlier_count=8,
        condition_number=100.0,
        inlier_mask=[True] * 8,
        calibration_quality="excellent",
    )


def test_monte_carlo_speed_posterior_is_reproducible() -> None:
    analyzer = CalibrationMonteCarloAnalyzer()

    left = analyzer.analyze(
        _homography(),
        speed_kmh=50.0,
        sample_count=64,
        scale_sigma_pct=0.04,
        random_seed=7,
    )
    right = analyzer.analyze(
        _homography(),
        speed_kmh=50.0,
        sample_count=64,
        scale_sigma_pct=0.04,
        random_seed=7,
    )

    assert left.to_dict() == right.to_dict()


def test_larger_scale_uncertainty_widens_speed_posterior() -> None:
    analyzer = CalibrationMonteCarloAnalyzer()

    narrow = analyzer.analyze(
        _homography(),
        speed_kmh=50.0,
        sample_count=128,
        scale_sigma_pct=0.01,
        random_seed=11,
    )
    wide = analyzer.analyze(
        _homography(),
        speed_kmh=50.0,
        sample_count=128,
        scale_sigma_pct=0.08,
        random_seed=11,
    )

    assert wide.std_kmh > narrow.std_kmh
    assert wide.p95_kmh - wide.p05_kmh > narrow.p95_kmh - narrow.p05_kmh


def test_speed_posterior_percentiles_are_ordered() -> None:
    posterior = CalibrationMonteCarloAnalyzer().analyze(
        _homography(),
        speed_kmh=35.0,
        sample_count=96,
        scale_sigma_pct=0.05,
        random_seed=13,
    )

    assert posterior.p05_kmh <= posterior.p50_kmh <= posterior.p95_kmh
    assert posterior.sample_count == 96
    assert posterior.model_reference == "homography_monte_carlo_speed_posterior"


def test_zero_speed_posterior_is_not_negative() -> None:
    posterior = CalibrationMonteCarloAnalyzer().analyze(
        _homography(),
        speed_kmh=0.0,
        sample_count=32,
        scale_sigma_pct=0.10,
        random_seed=17,
    )

    assert posterior.mean_kmh == 0.0
    assert posterior.p05_kmh == 0.0
    assert posterior.p95_kmh == 0.0
