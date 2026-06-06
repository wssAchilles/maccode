from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from domain.calibration.models import CalibrationPoint, HomographyResult
from domain.calibration.service import CalibrationService
from domain.speed.view_transformer import ViewTransformer


@dataclass(frozen=True)
class CalibrationCandidate:
    candidate_id: str
    source: str
    homography_matrix: NDArray[np.float64]
    trusted: bool
    metrics: dict[str, float | None]
    rejection_reasons: list[str]

    def to_dict(self) -> dict[str, object]:
        return {
            "candidate_id": self.candidate_id,
            "source": self.source,
            "trusted": self.trusted,
            "metrics": self.metrics,
            "rejection_reasons": self.rejection_reasons,
        }


@dataclass(frozen=True)
class CalibrationCandidateScore:
    candidate_id: str
    score: float
    breakdown: dict[str, float]
    trusted: bool
    rejection_reasons: list[str]

    def to_dict(self) -> dict[str, object]:
        return {
            "candidate_id": self.candidate_id,
            "score": self.score,
            "breakdown": self.breakdown,
            "trusted": self.trusted,
            "rejection_reasons": self.rejection_reasons,
        }


@dataclass(frozen=True)
class CalibrationCandidateEvaluation:
    candidates: list[CalibrationCandidate]
    scores: list[CalibrationCandidateScore]
    selected_candidate_id: str
    runtime_source: str

    def to_diagnostics(self) -> dict[str, object]:
        return {
            "calibration_candidates": [candidate.to_dict() for candidate in self.candidates],
            "selected_calibration_candidate_id": self.selected_candidate_id,
            "candidate_score_breakdown": {
                score.candidate_id: score.to_dict() for score in self.scores
            },
            "candidate_rejection_reasons": {
                score.candidate_id: score.rejection_reasons for score in self.scores
            },
        }


class CalibrationCandidateEvaluator:
    """Score homography candidates without aggressively overriding manual presets."""

    IMPROVEMENT_GATE = 0.20

    def evaluate(
        self,
        calibration: HomographyResult,
        calibration_context: dict[str, object],
        *,
        frame_width: int,
        frame_height: int,
    ) -> CalibrationCandidateEvaluation:
        candidates = [
            self._manual_candidate(calibration, calibration_context, frame_width, frame_height)
        ]
        three_d = self._three_d_candidate(
            calibration,
            calibration_context,
            frame_width,
            frame_height,
        )
        if three_d is not None:
            candidates.append(three_d)
        auto_candidate = self._auto_calibration_candidate(
            calibration,
            calibration_context,
            frame_width,
            frame_height,
        )
        if auto_candidate is not None:
            candidates.append(auto_candidate)

        scores = [self._score(candidate) for candidate in candidates]
        manual_score = scores[0]
        selected = candidates[0]
        selected_score = manual_score
        for candidate, score in zip(candidates[1:], scores[1:], strict=True):
            improvement = (manual_score.score - score.score) / max(manual_score.score, 1e-9)
            if score.trusted and not self._sensitivity_gate(candidates[0], candidate):
                index = scores.index(score)
                scores[index] = CalibrationCandidateScore(
                    candidate_id=score.candidate_id,
                    score=score.score,
                    breakdown=score.breakdown,
                    trusted=False,
                    rejection_reasons=[
                        *score.rejection_reasons,
                        "sensitivity_or_extrapolation_gate_failed",
                    ],
                )
                continue
            if score.trusted and improvement >= self.IMPROVEMENT_GATE:
                selected = candidate
                selected_score = score
                break
            if score.trusted:
                index = scores.index(score)
                scores[index] = CalibrationCandidateScore(
                    candidate_id=score.candidate_id,
                    score=score.score,
                    breakdown=score.breakdown,
                    trusted=False,
                    rejection_reasons=[
                        *score.rejection_reasons,
                        "improvement_below_20_percent_gate",
                    ],
                )
        return CalibrationCandidateEvaluation(
            candidates=candidates,
            scores=scores,
            selected_candidate_id=selected_score.candidate_id,
            runtime_source=selected.source,
        )

    @staticmethod
    def _sensitivity_gate(
        manual: CalibrationCandidate,
        candidate: CalibrationCandidate,
    ) -> bool:
        if candidate.source != "auto_vp_lane_vehicle_size_candidate":
            return True
        manual_scale = manual.metrics.get("local_scale_p95")
        candidate_scale = candidate.metrics.get("local_scale_p95")
        manual_extrapolation = manual.metrics.get("bev_grid_extrapolation_ratio")
        candidate_extrapolation = candidate.metrics.get("bev_grid_extrapolation_ratio")
        if (
            isinstance(manual_scale, int | float)
            and isinstance(candidate_scale, int | float)
            and float(candidate_scale) > float(manual_scale) * 1.05
        ):
            return False
        if (
            isinstance(manual_extrapolation, int | float)
            and isinstance(candidate_extrapolation, int | float)
            and float(candidate_extrapolation) > float(manual_extrapolation) + 0.02
        ):
            return False
        return True

    def _manual_candidate(
        self,
        calibration: HomographyResult,
        calibration_context: dict[str, object],
        frame_width: int,
        frame_height: int,
    ) -> CalibrationCandidate:
        trusted = bool(calibration_context.get("calibration_trusted", False))
        reasons: list[str] = []
        if not trusted:
            reasons.append("context_calibration_trusted_false")
        return CalibrationCandidate(
            candidate_id="manual_runtime_preset",
            source=calibration.runtime_homography_source,
            homography_matrix=np.asarray(calibration.homography_matrix, dtype=np.float64),
            trusted=trusted,
            metrics=self._metrics(calibration, calibration_context, frame_width, frame_height),
            rejection_reasons=reasons,
        )

    def _three_d_candidate(
        self,
        calibration: HomographyResult,
        calibration_context: dict[str, object],
        frame_width: int,
        frame_height: int,
    ) -> CalibrationCandidate | None:
        diagnostics = calibration_context.get("calibration_3d_diagnostics")
        if not isinstance(diagnostics, dict):
            return None
        candidate = diagnostics.get("h_pixel_to_world")
        try:
            matrix = np.asarray(candidate, dtype=np.float64)
        except (TypeError, ValueError):
            return None
        if matrix.shape != (3, 3) or not np.all(np.isfinite(matrix)):
            return None
        consistency = diagnostics.get("homography_consistency")
        consistency_passed = (
            isinstance(consistency, dict) and bool(consistency.get("passed", False))
        )
        trusted = bool(diagnostics.get("calibration_trusted", False)) and consistency_passed
        reasons: list[str] = []
        if not trusted:
            reasons.append("vehicle_3d_consistency_gate_failed")
        result = HomographyResult(
            homography_matrix=matrix,
            reprojection_rmse=calibration.reprojection_rmse,
            pixel_to_world_rmse_m=calibration.pixel_to_world_rmse_m,
            world_to_pixel_rmse_px=calibration.world_to_pixel_rmse_px,
            inlier_count=calibration.inlier_count,
            condition_number=calibration.condition_number,
            inlier_mask=list(calibration.inlier_mask),
            calibration_quality=calibration.calibration_quality,
            runtime_homography_source="vehicle_3d_prior_pnp",
        )
        metrics = self._metrics(result, calibration_context, frame_width, frame_height)
        metrics["manual_consistency_delta"] = self._matrix_delta(
            calibration.homography_matrix,
            matrix,
        )
        return CalibrationCandidate(
            candidate_id="vehicle_3d_prior_pnp",
            source="vehicle_3d_prior_pnp",
            homography_matrix=matrix,
            trusted=trusted,
            metrics=metrics,
            rejection_reasons=reasons,
        )

    def _auto_calibration_candidate(
        self,
        calibration: HomographyResult,
        calibration_context: dict[str, object],
        frame_width: int,
        frame_height: int,
    ) -> CalibrationCandidate | None:
        auto = calibration_context.get("auto_calibration")
        if not isinstance(auto, dict):
            return None
        proposal = auto.get("homography_proposal")
        if not isinstance(proposal, dict):
            return None
        raw_points = proposal.get("candidate_points")
        if not isinstance(raw_points, list):
            return None
        points: list[CalibrationPoint] = []
        for item in raw_points:
            if not isinstance(item, dict):
                return None
            pixel = item.get("pixel")
            world = item.get("world")
            if (
                not isinstance(pixel, (list, tuple))
                or not isinstance(world, (list, tuple))
                or len(pixel) != 2
                or len(world) != 2
            ):
                return None
            try:
                points.append(
                    CalibrationPoint(
                        pixel_x=float(pixel[0]),
                        pixel_y=float(pixel[1]),
                        world_x=float(world[0]),
                        world_y=float(world[1]),
                    )
                )
            except (TypeError, ValueError):
                return None
        if len(points) < 4:
            return None
        try:
            result = CalibrationService().compute_homography(points)
        except (ValueError, np.linalg.LinAlgError):
            return None
        confidence = self._optional_float(auto.get("auto_calibration_confidence")) or 0.0
        quality_issues = auto.get("quality_issues")
        reasons = [
            str(issue)
            for issue in quality_issues
            if isinstance(issue, str)
        ] if isinstance(quality_issues, list) else []
        trusted = confidence >= 0.85 and not reasons
        if not trusted:
            reasons.append("auto_calibration_confidence_or_quality_gate_failed")
        result = HomographyResult(
            homography_matrix=result.homography_matrix,
            reprojection_rmse=result.reprojection_rmse,
            pixel_to_world_rmse_m=result.pixel_to_world_rmse_m,
            world_to_pixel_rmse_px=result.world_to_pixel_rmse_px,
            inlier_count=result.inlier_count,
            condition_number=result.condition_number,
            inlier_mask=result.inlier_mask,
            calibration_quality=result.calibration_quality,
            refinement_applied=result.refinement_applied,
            refinement_initial_rmse_m=result.refinement_initial_rmse_m,
            refinement_final_rmse_m=result.refinement_final_rmse_m,
            refinement_iterations=result.refinement_iterations,
            runtime_homography_source="auto_vp_lane_vehicle_size_candidate",
        )
        metrics = self._metrics(result, calibration_context, frame_width, frame_height)
        metrics["auto_calibration_confidence"] = confidence
        metrics["manual_consistency_delta"] = self._matrix_delta(
            calibration.homography_matrix,
            result.homography_matrix,
        )
        return CalibrationCandidate(
            candidate_id="auto_vp_lane_vehicle_size_candidate",
            source="auto_vp_lane_vehicle_size_candidate",
            homography_matrix=result.homography_matrix,
            trusted=trusted,
            metrics=metrics,
            rejection_reasons=reasons,
        )

    def _metrics(
        self,
        calibration: HomographyResult,
        calibration_context: dict[str, object],
        frame_width: int,
        frame_height: int,
    ) -> dict[str, float | None]:
        local_scales = self._local_scale_samples(
            calibration.homography_matrix,
            frame_width,
            frame_height,
        )
        validation_error = self._optional_float(
            calibration_context.get("validation_max_error_px")
        )
        extrapolation_ratio = self._extrapolation_ratio(
            calibration_context.get("road_plane_polygon_world"),
            calibration.homography_matrix,
            frame_width,
            frame_height,
        )
        return {
            "control_point_residual_m": float(calibration.pixel_to_world_rmse_m),
            "validation_segment_residual_px": validation_error,
            "condition_number": float(calibration.condition_number),
            "local_scale_p75": self._percentile(local_scales, 75.0),
            "local_scale_p95": self._percentile(local_scales, 95.0),
            "bev_grid_extrapolation_ratio": extrapolation_ratio,
            "inlier_count": float(calibration.inlier_count),
        }

    @staticmethod
    def _score(candidate: CalibrationCandidate) -> CalibrationCandidateScore:
        m = candidate.metrics
        breakdown = {
            "control_point_residual": min(
                (m.get("control_point_residual_m") or 0.0) / 0.4,
                3.0,
            ),
            "validation_segment_residual": min(
                (m.get("validation_segment_residual_px") or 15.0) / 15.0,
                3.0,
            ),
            "condition_number": min(
                np.log10(max(m.get("condition_number") or 1.0, 1.0)) / 6.0,
                3.0,
            ),
            "local_scale": min((m.get("local_scale_p95") or 1.0) / 8.0, 3.0),
            "extrapolation": min(
                (m.get("bev_grid_extrapolation_ratio") or 0.0) * 2.0,
                3.0,
            ),
            "manual_consistency": min(
                (m.get("manual_consistency_delta") or 0.0) / 0.1,
                3.0,
            ),
        }
        score = (
            breakdown["control_point_residual"] * 0.25
            + breakdown["validation_segment_residual"] * 0.25
            + breakdown["condition_number"] * 0.15
            + breakdown["local_scale"] * 0.15
            + breakdown["extrapolation"] * 0.10
            + breakdown["manual_consistency"] * 0.10
        )
        reasons = list(candidate.rejection_reasons)
        if (m.get("validation_segment_residual_px") or 0.0) > 20.0:
            reasons.append("validation_segment_residual_high")
        if (m.get("local_scale_p95") or 1.0) > 12.0:
            reasons.append("local_scale_p95_high")
        if (m.get("condition_number") or 1.0) > 1e8:
            reasons.append("condition_number_high")
        trusted = candidate.trusted and not reasons
        return CalibrationCandidateScore(
            candidate_id=candidate.candidate_id,
            score=float(score),
            breakdown={key: float(value) for key, value in breakdown.items()},
            trusted=trusted,
            rejection_reasons=reasons,
        )

    @staticmethod
    def _local_scale_samples(
        matrix: NDArray[np.float64],
        frame_width: int,
        frame_height: int,
    ) -> list[float]:
        transformer = ViewTransformer(matrix)
        samples: list[float] = []
        for x_ratio in (0.1, 0.3, 0.5, 0.7, 0.9):
            for y_ratio in (0.1, 0.3, 0.5, 0.7, 0.9):
                try:
                    samples.append(
                        transformer.local_position_uncertainty(
                            frame_width * x_ratio,
                            frame_height * y_ratio,
                        ).local_scale_factor
                    )
                except ValueError:
                    samples.append(99.0)
        return samples

    @staticmethod
    def _extrapolation_ratio(
        polygon_value: object,
        matrix: NDArray[np.float64],
        frame_width: int,
        frame_height: int,
    ) -> float | None:
        polygon = CalibrationCandidateEvaluator._parse_polygon(polygon_value)
        if polygon is None:
            return None
        transformer = ViewTransformer(matrix)
        outside = 0
        total = 0
        for x_ratio in (0.1, 0.3, 0.5, 0.7, 0.9):
            for y_ratio in (0.1, 0.3, 0.5, 0.7, 0.9):
                total += 1
                world = transformer.transform_point(
                    frame_width * x_ratio,
                    frame_height * y_ratio,
                )
                if not CalibrationCandidateEvaluator._point_in_polygon(world, polygon):
                    outside += 1
        return outside / max(total, 1)

    @staticmethod
    def _parse_polygon(value: object) -> list[tuple[float, float]] | None:
        if not isinstance(value, list):
            return None
        polygon: list[tuple[float, float]] = []
        for point in value:
            if not isinstance(point, (list, tuple)) or len(point) != 2:
                return None
            try:
                polygon.append((float(point[0]), float(point[1])))
            except (TypeError, ValueError):
                return None
        return polygon if len(polygon) >= 3 else None

    @staticmethod
    def _point_in_polygon(
        point: tuple[float, float],
        polygon: list[tuple[float, float]],
    ) -> bool:
        x, y = point
        inside = False
        j = len(polygon) - 1
        for i, (xi, yi) in enumerate(polygon):
            xj, yj = polygon[j]
            if ((yi > y) != (yj > y)) and (
                x < (xj - xi) * (y - yi) / max(yj - yi, 1e-12) + xi
            ):
                inside = not inside
            j = i
        return inside

    @staticmethod
    def _percentile(values: list[float], percentile: float) -> float | None:
        if not values:
            return None
        return float(np.percentile(np.asarray(values, dtype=np.float64), percentile))

    @staticmethod
    def _optional_float(value: object) -> float | None:
        if value is None or isinstance(value, bool):
            return None
        if not isinstance(value, (int, float, str)):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _matrix_delta(
        left: NDArray[np.float64],
        right: NDArray[np.float64],
    ) -> float:
        left_norm = np.asarray(left, dtype=np.float64) / max(abs(float(left[2, 2])), 1e-12)
        right_norm = np.asarray(right, dtype=np.float64) / max(abs(float(right[2, 2])), 1e-12)
        denominator = max(float(np.linalg.norm(left_norm)), 1e-12)
        return float(np.linalg.norm(left_norm - right_norm) / denominator)
