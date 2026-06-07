from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from domain.calibration.models import HomographyResult
from domain.calibration.monte_carlo import CalibrationMonteCarloAnalyzer
from domain.speed.models import SpeedRecord


@dataclass(frozen=True)
class SpeedPosteriorSummary:
    mean_kmh: float
    std_kmh: float
    p05_kmh: float
    p50_kmh: float
    p95_kmh: float
    sample_count: int
    sources: list[str]
    model_reference: str = "joint_speed_uncertainty_posterior_v1"

    def to_dict(self) -> dict[str, object]:
        return {
            "mean_kmh": self.mean_kmh,
            "std_kmh": self.std_kmh,
            "p05_kmh": self.p05_kmh,
            "p50_kmh": self.p50_kmh,
            "p95_kmh": self.p95_kmh,
            "sample_count": self.sample_count,
            "sources": list(self.sources),
            "model_reference": self.model_reference,
        }


class SpeedPosteriorAnalyzer:
    """Code-side approximation of per-record speed posterior uncertainty."""

    _SOURCES = [
        "calibration_scale",
        "speed_uncertainty",
        "position_covariance",
        "timestamp_uncertainty",
    ]

    def analyze(
        self,
        record: SpeedRecord,
        calibration: HomographyResult,
        *,
        timestamp_uncertainty_sec: float = 0.0,
        sample_count: int = 200,
        random_seed: int | None = None,
    ) -> SpeedPosteriorSummary:
        if sample_count <= 0:
            raise ValueError("sample_count must be positive")
        if timestamp_uncertainty_sec < 0:
            raise ValueError("timestamp_uncertainty_sec must not be negative")

        nominal_speed = max(float(record.speed_kmh or 0.0), 0.0)
        rng = np.random.default_rng(random_seed)
        calibration_posterior = CalibrationMonteCarloAnalyzer().analyze(
            calibration,
            speed_kmh=nominal_speed,
            sample_count=sample_count,
            random_seed=random_seed,
        )
        calibration_centered = (
            rng.normal(
                0.0,
                max(calibration_posterior.std_kmh, 0.0),
                sample_count,
            )
            if nominal_speed > 0.0
            else np.zeros(sample_count, dtype=np.float64)
        )
        speed_noise = rng.normal(
            0.0,
            max(float(record.speed_uncertainty_kmh or 0.0), 0.0),
            sample_count,
        )
        position_noise = rng.normal(
            0.0,
            self._position_speed_sigma_kmh(record),
            sample_count,
        )
        timestamp_noise = rng.normal(
            0.0,
            nominal_speed * min(float(timestamp_uncertainty_sec), 1.0),
            sample_count,
        )
        samples = np.maximum(
            0.0,
            nominal_speed + calibration_centered + speed_noise + position_noise + timestamp_noise,
        )
        return SpeedPosteriorSummary(
            mean_kmh=float(np.mean(samples)),
            std_kmh=float(np.std(samples)),
            p05_kmh=float(np.percentile(samples, 5)),
            p50_kmh=float(np.percentile(samples, 50)),
            p95_kmh=float(np.percentile(samples, 95)),
            sample_count=int(sample_count),
            sources=list(self._SOURCES),
        )

    @staticmethod
    def _position_speed_sigma_kmh(record: SpeedRecord) -> float:
        if record.position_covariance is None:
            return 0.0
        covariance = np.asarray(record.position_covariance, dtype=np.float64)
        if covariance.shape != (2, 2):
            return 0.0
        variance = max(float(np.trace(covariance) / 2.0), 0.0)
        return float(variance**0.5 * 3.6)
