from __future__ import annotations

from typing import cast

import numpy as np
from domain.calibration.candidate_evaluation import CalibrationCandidateEvaluator
from domain.calibration.models import HomographyResult


def _homography(matrix: np.ndarray, rmse: float = 0.1) -> HomographyResult:
    return HomographyResult(
        homography_matrix=matrix.astype(float),
        reprojection_rmse=rmse,
        pixel_to_world_rmse_m=rmse,
        world_to_pixel_rmse_px=1.0,
        inlier_count=8,
        condition_number=100.0,
        inlier_mask=[True] * 8,
        calibration_quality="excellent",
        runtime_homography_source="video_manual_preset",
    )


def test_manual_preset_is_default_when_candidate_improvement_is_small() -> None:
    manual = _homography(np.eye(3), rmse=0.1)
    context = {
        "calibration_trusted": True,
        "validation_max_error_px": 5.0,
        "calibration_3d_diagnostics": {
            "calibration_trusted": True,
            "homography_consistency": {"passed": True},
            "h_pixel_to_world": np.eye(3).tolist(),
        },
    }

    evaluation = CalibrationCandidateEvaluator().evaluate(
        manual,
        context,
        frame_width=100,
        frame_height=100,
    )

    assert evaluation.selected_candidate_id == "manual_runtime_preset"
    diagnostics = evaluation.to_diagnostics()
    rejection_reasons = diagnostics["candidate_rejection_reasons"]
    assert isinstance(rejection_reasons, dict)
    typed_reasons = cast(dict[str, list[str]], rejection_reasons)
    assert "improvement_below_20_percent_gate" in typed_reasons[
        "vehicle_3d_prior_pnp"
    ]


def test_untrusted_3d_candidate_cannot_override_manual_runtime() -> None:
    manual = _homography(np.eye(3), rmse=0.1)
    context = {
        "calibration_trusted": True,
        "validation_max_error_px": 5.0,
        "calibration_3d_diagnostics": {
            "calibration_trusted": False,
            "homography_consistency": {"passed": False},
            "h_pixel_to_world": [[0.01, 0, 0], [0, 0.01, 0], [0, 0, 1]],
        },
    }

    evaluation = CalibrationCandidateEvaluator().evaluate(
        manual,
        context,
        frame_width=100,
        frame_height=100,
    )

    assert evaluation.selected_candidate_id == "manual_runtime_preset"
    diagnostics = evaluation.to_diagnostics()
    rejection_reasons = diagnostics["candidate_rejection_reasons"]
    assert isinstance(rejection_reasons, dict)
    typed_reasons = cast(dict[str, list[str]], rejection_reasons)
    assert "vehicle_3d_consistency_gate_failed" in typed_reasons["vehicle_3d_prior_pnp"]
