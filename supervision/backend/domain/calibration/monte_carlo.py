from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from domain.calibration.models import HomographyResult


@dataclass(frozen=True)
class CalibrationSpeedPosterior:
    mean_kmh: float
    std_kmh: float
    p05_kmh: float
    p50_kmh: float
    p95_kmh: float
    sample_count: int
    model_reference: str = "homography_monte_carlo_speed_posterior"

    def to_dict(self) -> dict[str, object]:
        return {
            "mean_kmh": self.mean_kmh,
            "std_kmh": self.std_kmh,
            "p05_kmh": self.p05_kmh,
            "p50_kmh": self.p50_kmh,
            "p95_kmh": self.p95_kmh,
            "sample_count": self.sample_count,
            "model_reference": self.model_reference,
        }


class CalibrationMonteCarloAnalyzer:
    """Approximates speed posterior width from calibration scale uncertainty."""

    def analyze(
        self,
        calibration: HomographyResult,
        *,
        speed_kmh: float,
        sample_count: int = 200,
        scale_sigma_pct: float = 0.03,
        random_seed: int | None = None,
    ) -> CalibrationSpeedPosterior:
        if sample_count <= 0:
            raise ValueError("sample_count must be positive")
        if scale_sigma_pct < 0:
            raise ValueError("scale_sigma_pct must not be negative")
        nominal_speed = max(float(speed_kmh), 0.0)
        if nominal_speed == 0.0:
            samples = np.zeros(sample_count, dtype=np.float64)
        else:
            rng = np.random.default_rng(random_seed)
            quality_scale = self._quality_scale(calibration)
            sigma = float(scale_sigma_pct) * quality_scale
            scale_samples = rng.normal(loc=1.0, scale=max(sigma, 0.0), size=sample_count)
            samples = np.maximum(0.0, nominal_speed * scale_samples)
        return CalibrationSpeedPosterior(
            mean_kmh=float(np.mean(samples)),
            std_kmh=float(np.std(samples)),
            p05_kmh=float(np.percentile(samples, 5)),
            p50_kmh=float(np.percentile(samples, 50)),
            p95_kmh=float(np.percentile(samples, 95)),
            sample_count=int(sample_count),
        )

    @staticmethod
    def _quality_scale(calibration: HomographyResult) -> float:
        rmse_factor = 1.0 + max(float(calibration.pixel_to_world_rmse_m), 0.0)
        condition_factor = 1.0 + min(max(float(calibration.condition_number), 1.0) / 1e6, 1.0)
        inlier_factor = 1.0 + 1.0 / max(float(calibration.inlier_count), 1.0)
        return float(rmse_factor * condition_factor * inlier_factor)
