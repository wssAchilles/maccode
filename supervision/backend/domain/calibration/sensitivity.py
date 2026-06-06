from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import NDArray

from domain.calibration.bev_confidence import BEVConfidenceMap
from domain.calibration.models import HomographyResult
from domain.speed.view_transformer import ViewTransformer


@dataclass(frozen=True)
class CalibrationSensitivityReport:
    perturbation_px: float
    speed_sensitivity_p50: float
    speed_sensitivity_p95: float
    calibration_uncertainty_band_kmh: tuple[float | None, float | None]
    rejected_ratio_delta: float
    sample_count: int
    model_reference: str = "homography_perturbation_sensitivity"

    def to_dict(self) -> dict[str, object]:
        return {
            "perturbation_px": self.perturbation_px,
            "speed_sensitivity_p50": self.speed_sensitivity_p50,
            "speed_sensitivity_p95": self.speed_sensitivity_p95,
            "calibration_uncertainty_band_kmh": list(self.calibration_uncertainty_band_kmh),
            "rejected_ratio_delta": self.rejected_ratio_delta,
            "sample_count": self.sample_count,
            "model_reference": self.model_reference,
        }


class CalibrationSensitivityAnalyzer:
    """Audits how much local geometry can amplify downstream speed estimates."""

    def analyze(
        self,
        calibration: HomographyResult,
        bev_confidence_map: BEVConfidenceMap,
        calibration_context: dict[str, object],
        *,
        speed_kmh: float | None = None,
        perturbation_px: float = 1.5,
    ) -> CalibrationSensitivityReport:
        matrix = np.asarray(calibration.homography_matrix, dtype=np.float64)
        baseline_scale = self._local_scales(matrix, bev_confidence_map)
        if not baseline_scale:
            return CalibrationSensitivityReport(
                perturbation_px=perturbation_px,
                speed_sensitivity_p50=0.0,
                speed_sensitivity_p95=0.0,
                calibration_uncertainty_band_kmh=(speed_kmh, speed_kmh),
                rejected_ratio_delta=0.0,
                sample_count=0,
            )

        sensitivities: list[float] = []
        for offset in self._matrix_offsets(perturbation_px):
            perturbed = matrix + offset
            perturbed[2, 2] = matrix[2, 2]
            perturbed_scale = self._local_scales(perturbed, bev_confidence_map)
            if len(perturbed_scale) != len(baseline_scale):
                continue
            ratios = [
                abs(candidate - base) / max(abs(base), 1e-6)
                for candidate, base in zip(perturbed_scale, baseline_scale, strict=True)
            ]
            sensitivities.extend(ratios)

        if not sensitivities:
            sensitivities = [0.0]
        p50 = float(np.percentile(np.asarray(sensitivities, dtype=np.float64), 50))
        p95 = float(np.percentile(np.asarray(sensitivities, dtype=np.float64), 95))
        band: tuple[float | None, float | None]
        if speed_kmh is None:
            band = (None, None)
        else:
            margin = max(0.0, speed_kmh * p95)
            band = (max(0.0, speed_kmh - margin), speed_kmh + margin)
        rejected_ratio = self._rejected_ratio(bev_confidence_map)
        expected_delta = self._expected_rejected_delta(calibration_context, p95)
        return CalibrationSensitivityReport(
            perturbation_px=perturbation_px,
            speed_sensitivity_p50=p50,
            speed_sensitivity_p95=p95,
            calibration_uncertainty_band_kmh=band,
            rejected_ratio_delta=max(0.0, expected_delta - rejected_ratio),
            sample_count=len(sensitivities),
        )

    @staticmethod
    def _local_scales(
        matrix: NDArray[np.float64],
        bev_confidence_map: BEVConfidenceMap,
    ) -> list[float]:
        transformer = ViewTransformer(matrix)
        scales: list[float] = []
        for cell in bev_confidence_map.cells:
            try:
                scales.append(
                    float(
                        transformer.local_position_uncertainty(
                            cell.pixel[0],
                            cell.pixel[1],
                        ).local_scale_factor
                    )
                )
            except ValueError:
                continue
        return scales

    @staticmethod
    def _matrix_offsets(perturbation_px: float) -> list[NDArray[np.float64]]:
        scale = max(perturbation_px, 0.0) * 1e-3
        offsets: list[NDArray[np.float64]] = []
        for row, col in ((0, 0), (0, 1), (1, 0), (1, 1), (2, 0), (2, 1)):
            for sign in (-1.0, 1.0):
                offset = np.zeros((3, 3), dtype=np.float64)
                offset[row, col] = sign * scale
                offsets.append(offset)
        return offsets

    @staticmethod
    def _rejected_ratio(bev_confidence_map: BEVConfidenceMap) -> float:
        total = max(len(bev_confidence_map.cells), 1)
        return sum(1 for cell in bev_confidence_map.cells if cell.risk_level == "rejected") / total

    @staticmethod
    def _expected_rejected_delta(
        calibration_context: dict[str, object],
        sensitivity_p95: float,
    ) -> float:
        validation = calibration_context.get("validation_max_error_px")
        validation_penalty = (
            min(float(validation) / 100.0, 0.25)
            if isinstance(validation, int | float)
            else 0.0
        )
        return min(1.0, sensitivity_p95 + validation_penalty)


def sensitivity_summary_from_tracks(
    tracks: list[dict[str, Any]],
    default_band: tuple[float | None, float | None],
) -> dict[str, object]:
    bands = [
        track.get("calibration_uncertainty_band_kmh")
        for track in tracks
        if isinstance(track, dict)
        and isinstance(track.get("calibration_uncertainty_band_kmh"), list)
    ]
    return {
        "track_band_count": len(bands),
        "default_calibration_uncertainty_band_kmh": list(default_band),
    }
