from __future__ import annotations

import numpy as np
from domain.calibration.bev_confidence import BEVConfidenceMapBuilder
from domain.calibration.models import HomographyResult
from domain.calibration.sensitivity import CalibrationSensitivityAnalyzer
from domain.speed.view_transformer import ViewTransformer


def _homography(scale: float = 0.1) -> HomographyResult:
    matrix = np.array([[scale, 0.0, 0.0], [0.0, scale, 0.0], [0.0, 0.001, 1.0]])
    return HomographyResult(
        homography_matrix=matrix,
        reprojection_rmse=0.1,
        pixel_to_world_rmse_m=0.1,
        world_to_pixel_rmse_px=1.0,
        inlier_count=8,
        condition_number=100.0,
        inlier_mask=[True] * 8,
        calibration_quality="excellent",
        runtime_homography_source="video_manual_preset",
    )


def test_larger_homography_perturbation_widens_speed_uncertainty_band() -> None:
    calibration = _homography()
    confidence_map = BEVConfidenceMapBuilder(
        ViewTransformer(calibration.homography_matrix),
        frame_width=320,
        frame_height=240,
    ).build()

    small = CalibrationSensitivityAnalyzer().analyze(
        calibration,
        confidence_map,
        {},
        speed_kmh=50.0,
        perturbation_px=0.5,
    )
    large = CalibrationSensitivityAnalyzer().analyze(
        calibration,
        confidence_map,
        {},
        speed_kmh=50.0,
        perturbation_px=4.0,
    )

    assert large.speed_sensitivity_p95 > small.speed_sensitivity_p95
    large_low, large_high = large.calibration_uncertainty_band_kmh
    small_low, small_high = small.calibration_uncertainty_band_kmh
    assert large_low is not None
    assert large_high is not None
    assert small_low is not None
    assert small_high is not None
    assert large_low < small_low
    assert large_high > small_high
