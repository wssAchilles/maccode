from __future__ import annotations

import math

from domain.auto_calibration.models import (
    AutoCalibrationDiagnostics,
    AutoHomographyProposal,
    CandidateLine,
)
from domain.calibration.models import CalibrationPoint
from domain.calibration.service import CalibrationService


class AutoCalibrationService:
    def diagnose(
        self,
        candidate_lines: list[CandidateLine],
        scale_prior_used: str | None,
        manual_profile_available: bool,
        evidence_sources: list[str] | None = None,
        world_width_m: float | None = None,
        world_length_m: float | None = None,
    ) -> AutoCalibrationDiagnostics:
        vanishing_points = self._estimate_vanishing_points(candidate_lines)
        homography_proposal = self._build_homography_proposal(
            candidate_lines,
            world_width_m,
            world_length_m,
        )
        issues: list[str] = []
        if len(candidate_lines) < 2:
            issues.append("insufficient_candidate_lines")
        if not vanishing_points:
            issues.append("no_parallel_line_intersection")
        if scale_prior_used is None:
            issues.append("missing_scale_prior")
        if homography_proposal is None:
            issues.append("no_homography_proposal")

        confidence = 0.0
        if len(candidate_lines) >= 2:
            confidence += 0.25
        if vanishing_points:
            confidence += 0.25
        if scale_prior_used:
            confidence += 0.20
        if homography_proposal is not None:
            confidence += 0.10
        confidence = min(confidence, 0.7)

        selected_strategy = (
            "manual_camera_profile_fallback"
            if manual_profile_available and confidence < 0.75
            else "auto_homography_candidate"
        )
        if selected_strategy == "manual_camera_profile_fallback":
            issues.append("auto_confidence_below_manual_profile_gate")

        return AutoCalibrationDiagnostics(
            confidence=confidence,
            candidate_lines=candidate_lines,
            vanishing_points=vanishing_points,
            scale_prior_used=scale_prior_used,
            quality_issues=issues,
            selected_strategy=selected_strategy,
            evidence_sources=evidence_sources or ["profile_candidate_lines"],
            homography_proposal=homography_proposal,
        )

    @staticmethod
    def _build_homography_proposal(
        candidate_lines: list[CandidateLine],
        world_width_m: float | None,
        world_length_m: float | None,
    ) -> AutoHomographyProposal | None:
        if world_width_m is None or world_length_m is None:
            return None
        if world_width_m <= 0 or world_length_m <= 0:
            return None
        perspective_lines = [
            line
            for line in candidate_lines
            if "edge" in line.kind or "lane" in line.kind or "bundle" in line.kind
        ]
        if len(perspective_lines) < 2:
            return None
        left, right = AutoCalibrationService._select_outer_lines(perspective_lines[:8])
        if left is None or right is None:
            return None
        left_bottom, left_top = AutoCalibrationService._bottom_top_points(left)
        right_bottom, right_top = AutoCalibrationService._bottom_top_points(right)
        if left_bottom[0] > right_bottom[0]:
            left_bottom, right_bottom = right_bottom, left_bottom
            left_top, right_top = right_top, left_top
        proposal_points = [
            CalibrationPoint(left_bottom[0], left_bottom[1], 0.0, 0.0),
            CalibrationPoint(right_bottom[0], right_bottom[1], world_width_m, 0.0),
            CalibrationPoint(right_top[0], right_top[1], world_width_m, world_length_m),
            CalibrationPoint(left_top[0], left_top[1], 0.0, world_length_m),
        ]
        try:
            result = CalibrationService().compute_homography_ransac(
                proposal_points,
                reprojection_threshold=1.0,
                max_iterations=30,
                random_seed=17,
            )
        except ValueError:
            return None
        return AutoHomographyProposal(
            method="candidate_trapezoid_dlt_ransac",
            candidate_points=proposal_points,
            inlier_count=result.inlier_count,
            reprojection_rmse=result.reprojection_rmse,
            condition_number=result.condition_number,
            calibration_quality=result.calibration_quality,
        )

    @staticmethod
    def _select_outer_lines(
        lines: list[CandidateLine],
    ) -> tuple[CandidateLine | None, CandidateLine | None]:
        if len(lines) < 2:
            return (None, None)
        sorted_lines = sorted(lines, key=lambda line: (line.start[0] + line.end[0]) / 2.0)
        return (sorted_lines[0], sorted_lines[-1])

    @staticmethod
    def _bottom_top_points(line: CandidateLine) -> tuple[tuple[float, float], tuple[float, float]]:
        if line.start[1] >= line.end[1]:
            return (line.start, line.end)
        return (line.end, line.start)

    @staticmethod
    def _estimate_vanishing_points(
        candidate_lines: list[CandidateLine],
    ) -> list[tuple[float, float]]:
        points: list[tuple[float, float]] = []
        for index, first in enumerate(candidate_lines):
            for second in candidate_lines[index + 1 :]:
                if first.kind != second.kind:
                    continue
                intersection = AutoCalibrationService._line_intersection(first, second)
                if intersection is not None:
                    points.append(intersection)
        return points[:3]

    @staticmethod
    def _line_intersection(
        first: CandidateLine,
        second: CandidateLine,
    ) -> tuple[float, float] | None:
        x1, y1 = first.start
        x2, y2 = first.end
        x3, y3 = second.start
        x4, y4 = second.end
        denominator = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if math.isclose(denominator, 0.0, abs_tol=1e-9):
            return None
        px = ((x1 * y2 - y1 * x2) * (x3 - x4) - (x1 - x2) * (x3 * y4 - y3 * x4))
        py = ((x1 * y2 - y1 * x2) * (y3 - y4) - (y1 - y2) * (x3 * y4 - y3 * x4))
        return (float(px / denominator), float(py / denominator))
