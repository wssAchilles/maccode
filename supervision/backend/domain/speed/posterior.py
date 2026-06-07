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
    position_mean_xy: list[float] | None = None
    position_covariance: list[list[float]] | None = None
    velocity_mean_xy: list[float] | None = None
    velocity_covariance: list[list[float]] | None = None
    speed_p05_p50_p95_kmh: list[float] | None = None
    uncertainty_components: dict[str, float] | None = None
    dominant_uncertainty_source: str | None = None
    posterior_reliability_label: str | None = None
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
            "position_mean_xy": self.position_mean_xy,
            "position_covariance": self.position_covariance,
            "velocity_mean_xy": self.velocity_mean_xy,
            "velocity_covariance": self.velocity_covariance,
            "speed_mean_kmh": self.mean_kmh,
            "speed_p05_p50_p95_kmh": self.speed_p05_p50_p95_kmh,
            "uncertainty_components": dict(self.uncertainty_components or {}),
            "dominant_uncertainty_source": self.dominant_uncertainty_source,
            "posterior_reliability_label": self.posterior_reliability_label,
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
        components = {
            "Sigma_scale": float(np.std(calibration_centered)),
            "Sigma_pixel": float(np.std(position_noise)),
            "Sigma_speed": float(np.std(speed_noise)),
            "Sigma_time": float(np.std(timestamp_noise)),
            "Sigma_tracking": self._tracking_sigma_kmh(record),
            "Sigma_H": self._homography_sigma_kmh(record, calibration, nominal_speed),
        }
        samples = np.maximum(
            0.0,
            nominal_speed
            + calibration_centered
            + speed_noise
            + position_noise
            + timestamp_noise
            + rng.normal(0.0, components["Sigma_tracking"], sample_count)
            + rng.normal(0.0, components["Sigma_H"], sample_count),
        )
        p05 = float(np.percentile(samples, 5))
        p50 = float(np.percentile(samples, 50))
        p95 = float(np.percentile(samples, 95))
        dominant = max(components.items(), key=lambda item: item[1])[0]
        std = float(np.std(samples))
        return SpeedPosteriorSummary(
            mean_kmh=float(np.mean(samples)),
            std_kmh=std,
            p05_kmh=p05,
            p50_kmh=p50,
            p95_kmh=p95,
            sample_count=int(sample_count),
            sources=list(self._SOURCES),
            position_mean_xy=[float(record.world_x), float(record.world_y)],
            position_covariance=record.position_covariance,
            velocity_mean_xy=[
                float(record.velocity_x_mps or 0.0),
                float(record.velocity_y_mps or 0.0),
            ],
            velocity_covariance=self._velocity_covariance(record, timestamp_uncertainty_sec),
            speed_p05_p50_p95_kmh=[p05, p50, p95],
            uncertainty_components=components,
            dominant_uncertainty_source=dominant,
            posterior_reliability_label=self._reliability_label(std, nominal_speed),
            model_reference="joint_speed_uncertainty_posterior_v1",
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

    @staticmethod
    def _tracking_sigma_kmh(record: SpeedRecord) -> float:
        risk = max(float(record.id_switch_risk or 0.0), 0.0)
        if record.speed_frozen:
            risk = max(risk, 0.45)
        state = (record.tracking_integrity_state or "").lower()
        if any(token in state for token in ("switch", "fragment", "lost", "relinked")):
            risk = max(risk, 0.6)
        return float(max(record.speed_kmh or 0.0, 1.0) * min(risk, 1.0) * 0.25)

    @staticmethod
    def _homography_sigma_kmh(
        record: SpeedRecord,
        calibration: HomographyResult,
        nominal_speed: float,
    ) -> float:
        rmse_term = max(float(calibration.pixel_to_world_rmse_m), 0.0)
        condition_term = min(max(float(calibration.condition_number), 1.0) / 1e6, 1.0)
        diagnostics = record.speed_geometry_diagnostics or {}
        validation_px = diagnostics.get("validation_max_error_px")
        validation_term = (
            min(max(float(validation_px), 0.0) / 40.0, 1.0)
            if isinstance(validation_px, int | float)
            else 0.0
        )
        sigma_ratio = min(
            0.5,
            0.03 + rmse_term * 0.08 + condition_term * 0.08 + validation_term * 0.12,
        )
        return float(max(nominal_speed, 1.0) * sigma_ratio)

    @staticmethod
    def _velocity_covariance(
        record: SpeedRecord,
        timestamp_uncertainty_sec: float,
    ) -> list[list[float]]:
        if record.position_covariance is None:
            base = max(float(record.speed_uncertainty_kmh or 0.0) / 3.6, 0.0) ** 2
            return [[base, 0.0], [0.0, base]]
        covariance = np.asarray(record.position_covariance, dtype=np.float64)
        if covariance.shape != (2, 2):
            return [[0.0, 0.0], [0.0, 0.0]]
        dt = max(float(timestamp_uncertainty_sec), 1e-3)
        return (covariance / (dt**2)).astype(float).tolist()

    @staticmethod
    def _reliability_label(std_kmh: float, nominal_speed: float) -> str:
        ratio = std_kmh / max(nominal_speed, 1.0)
        if ratio <= 0.15:
            return "high"
        if ratio <= 0.35:
            return "medium"
        return "low"
