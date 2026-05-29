from __future__ import annotations

from dataclasses import dataclass

from domain.calibration.models import CalibrationPoint


@dataclass(frozen=True)
class CandidateLine:
    name: str
    start: tuple[float, float]
    end: tuple[float, float]
    kind: str = "road_edge"

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "start": list(self.start),
            "end": list(self.end),
            "kind": self.kind,
        }


@dataclass(frozen=True)
class AutoHomographyProposal:
    method: str
    candidate_points: list[CalibrationPoint]
    inlier_count: int
    reprojection_rmse: float
    condition_number: float
    calibration_quality: str

    def to_dict(self) -> dict[str, object]:
        return {
            "method": self.method,
            "candidate_points": [
                {
                    "pixel": [point.pixel_x, point.pixel_y],
                    "world": [point.world_x, point.world_y],
                }
                for point in self.candidate_points
            ],
            "inlier_count": self.inlier_count,
            "reprojection_rmse": self.reprojection_rmse,
            "condition_number": self.condition_number,
            "calibration_quality": self.calibration_quality,
        }


@dataclass(frozen=True)
class AutoCalibrationDiagnostics:
    confidence: float
    candidate_lines: list[CandidateLine]
    vanishing_points: list[tuple[float, float]]
    scale_prior_used: str | None
    quality_issues: list[str]
    selected_strategy: str
    evidence_sources: list[str]
    homography_proposal: AutoHomographyProposal | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "auto_calibration_confidence": self.confidence,
            "candidate_lines": [line.to_dict() for line in self.candidate_lines],
            "vanishing_points": [list(point) for point in self.vanishing_points],
            "scale_prior_used": self.scale_prior_used,
            "quality_issues": self.quality_issues,
            "selected_strategy": self.selected_strategy,
            "evidence_sources": self.evidence_sources,
            "homography_proposal": self.homography_proposal.to_dict()
            if self.homography_proposal is not None
            else None,
        }
