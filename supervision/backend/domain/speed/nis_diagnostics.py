from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from domain.speed.models import SpeedRecord


@dataclass(frozen=True)
class NISDiagnosticsSummary:
    sample_count: int
    mean_nis: float | None
    median_nis: float | None
    p95_nis: float | None
    target_nis: float
    high_nis_ratio: float
    low_nis_ratio: float
    mean_adaptive_multiplier: float | None
    consistency_label: str
    recommendation: str
    model_reference: str = "nis_consistency_diagnostics_v1"

    def to_dict(self) -> dict[str, object]:
        return {
            "sample_count": self.sample_count,
            "mean_nis": self.mean_nis,
            "median_nis": self.median_nis,
            "p95_nis": self.p95_nis,
            "target_nis": self.target_nis,
            "high_nis_ratio": self.high_nis_ratio,
            "low_nis_ratio": self.low_nis_ratio,
            "mean_adaptive_multiplier": self.mean_adaptive_multiplier,
            "consistency_label": self.consistency_label,
            "recommendation": self.recommendation,
            "model_reference": self.model_reference,
        }


class NISDiagnosticsAnalyzer:
    def __init__(
        self,
        *,
        target_nis: float = 2.0,
        high_nis_threshold: float = 5.99,
        low_nis_threshold: float = 0.2,
        min_sample_count: int = 8,
    ) -> None:
        self.target_nis = target_nis
        self.high_nis_threshold = high_nis_threshold
        self.low_nis_threshold = low_nis_threshold
        self.min_sample_count = min_sample_count

    def analyze(self, records: list[SpeedRecord] | dict[int, SpeedRecord]) -> NISDiagnosticsSummary:
        iterable = records.values() if isinstance(records, dict) else records
        valid_records = [
            record
            for record in iterable
            if record.physics_valid
            and record.speed_kmh is not None
            and record.innovation_nis is not None
        ]
        nis_list: list[float] = []
        for record in valid_records:
            nis = record.innovation_nis
            if nis is not None:
                nis_list.append(float(nis))
        nis_values = np.asarray(nis_list, dtype=np.float64)
        multipliers: list[float] = []
        for record in valid_records:
            multiplier = record.adaptive_measurement_noise_multiplier
            if multiplier is not None:
                multipliers.append(float(multiplier))
        sample_count = int(nis_values.size)
        if sample_count == 0:
            return self._summary(
                sample_count=0,
                mean_nis=None,
                median_nis=None,
                p95_nis=None,
                high_nis_ratio=0.0,
                low_nis_ratio=0.0,
                mean_adaptive_multiplier=None,
                consistency_label="insufficient_samples",
                recommendation="collect more valid innovation samples",
            )

        high_ratio = float(np.mean(nis_values > self.high_nis_threshold))
        low_ratio = float(np.mean(nis_values < self.low_nis_threshold))
        mean_nis = float(np.mean(nis_values))
        label = "well_calibrated"
        recommendation = "keep current measurement-noise calibration"
        if sample_count < self.min_sample_count:
            label = "insufficient_samples"
            recommendation = "collect more valid innovation samples"
        elif high_ratio > 0.5 or mean_nis > self.target_nis * 2.0:
            label = "underestimated_measurement_noise"
            recommendation = "increase measurement noise or inspect contact/tracking outliers"
        elif low_ratio > 0.5 or mean_nis < self.target_nis * 0.35:
            label = "overestimated_measurement_noise"
            recommendation = "decrease measurement noise or relax adaptive R multiplier"

        return self._summary(
            sample_count=sample_count,
            mean_nis=mean_nis,
            median_nis=float(np.median(nis_values)),
            p95_nis=float(np.percentile(nis_values, 95)),
            high_nis_ratio=high_ratio,
            low_nis_ratio=low_ratio,
            mean_adaptive_multiplier=(
                float(np.mean(np.asarray(multipliers, dtype=np.float64)))
                if multipliers
                else None
            ),
            consistency_label=label,
            recommendation=recommendation,
        )

    def _summary(
        self,
        *,
        sample_count: int,
        mean_nis: float | None,
        median_nis: float | None,
        p95_nis: float | None,
        high_nis_ratio: float,
        low_nis_ratio: float,
        mean_adaptive_multiplier: float | None,
        consistency_label: str,
        recommendation: str,
    ) -> NISDiagnosticsSummary:
        return NISDiagnosticsSummary(
            sample_count=sample_count,
            mean_nis=mean_nis,
            median_nis=median_nis,
            p95_nis=p95_nis,
            target_nis=self.target_nis,
            high_nis_ratio=high_nis_ratio,
            low_nis_ratio=low_nis_ratio,
            mean_adaptive_multiplier=mean_adaptive_multiplier,
            consistency_label=consistency_label,
            recommendation=recommendation,
        )
