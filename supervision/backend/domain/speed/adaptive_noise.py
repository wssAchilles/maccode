from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AdaptiveMeasurementNoiseState:
    multiplier: float
    ewma_nis: float
    accepted_sample_count: int
    skipped_outlier_count: int


class AdaptiveMeasurementNoiseController:
    """Adapts measurement noise from normalized innovation statistics."""

    def __init__(
        self,
        *,
        target_nis: float = 2.0,
        alpha: float = 0.15,
        min_multiplier: float = 0.5,
        max_multiplier: float = 6.0,
        outlier_nis_threshold: float = 16.0,
    ) -> None:
        if target_nis <= 0:
            raise ValueError("target_nis must be positive")
        if not 0 < alpha <= 1:
            raise ValueError("alpha must be in (0, 1]")
        if min_multiplier <= 0 or max_multiplier < min_multiplier:
            raise ValueError("invalid multiplier bounds")
        if outlier_nis_threshold <= target_nis:
            raise ValueError("outlier_nis_threshold must exceed target_nis")
        self.target_nis = float(target_nis)
        self.alpha = float(alpha)
        self.min_multiplier = float(min_multiplier)
        self.max_multiplier = float(max_multiplier)
        self.outlier_nis_threshold = float(outlier_nis_threshold)
        self._ewma_nis = self.target_nis
        self._accepted_sample_count = 0
        self._skipped_outlier_count = 0

    @property
    def state(self) -> AdaptiveMeasurementNoiseState:
        return AdaptiveMeasurementNoiseState(
            multiplier=self.multiplier,
            ewma_nis=self._ewma_nis,
            accepted_sample_count=self._accepted_sample_count,
            skipped_outlier_count=self._skipped_outlier_count,
        )

    @property
    def multiplier(self) -> float:
        raw = self._ewma_nis / self.target_nis
        return float(min(self.max_multiplier, max(self.min_multiplier, raw)))

    def update(self, nis: float) -> AdaptiveMeasurementNoiseState:
        bounded_nis = max(float(nis), 0.0)
        if bounded_nis > self.outlier_nis_threshold:
            self._skipped_outlier_count += 1
            return self.state
        self._ewma_nis = (
            (1.0 - self.alpha) * self._ewma_nis
            + self.alpha * bounded_nis
        )
        self._accepted_sample_count += 1
        return self.state
