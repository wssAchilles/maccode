from __future__ import annotations

from domain.calibration.models import CalibrationPoint
from domain.calibration.service import CalibrationService


def test_ransac_homography_rejects_outlier_and_refits_inliers() -> None:
    service = CalibrationService()
    inliers = [
        CalibrationPoint(0, 0, 0, 0),
        CalibrationPoint(100, 0, 10, 0),
        CalibrationPoint(100, 100, 10, 10),
        CalibrationPoint(0, 100, 0, 10),
        CalibrationPoint(50, 0, 5, 0),
        CalibrationPoint(50, 100, 5, 10),
    ]
    outlier = CalibrationPoint(75, 75, 100, 100)

    direct = service.compute_homography([*inliers, outlier])
    robust = service.compute_homography_ransac(
        [*inliers, outlier],
        reprojection_threshold=0.25,
        max_iterations=200,
        random_seed=7,
    )

    assert robust.inlier_count == len(inliers)
    assert robust.inlier_mask == [True, True, True, True, True, True, False]
    assert robust.reprojection_rmse < 1e-6
    assert robust.reprojection_rmse < direct.reprojection_rmse
    assert robust.calibration_quality == "excellent"


def test_calibration_quality_degrades_when_reprojection_error_is_high() -> None:
    service = CalibrationService()
    points = [
        CalibrationPoint(0, 0, 0, 0),
        CalibrationPoint(100, 0, 10, 0),
        CalibrationPoint(100, 100, 10, 10),
        CalibrationPoint(0, 100, 0, 10),
        CalibrationPoint(50, 50, 8, 8),
    ]

    result = service.compute_homography(points)

    assert result.reprojection_rmse > 0.5
    assert result.calibration_quality in {"usable", "unstable"}
