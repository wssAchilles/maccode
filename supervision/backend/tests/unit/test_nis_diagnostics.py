from __future__ import annotations

from domain.speed.models import SpeedRecord
from domain.speed.nis_diagnostics import NISDiagnosticsAnalyzer


def _record(
    nis: float | None,
    *,
    physics_valid: bool = True,
    speed_kmh: float | None = 30.0,
    multiplier: float | None = 1.0,
) -> SpeedRecord:
    return SpeedRecord(
        tracker_id=1,
        speed_kmh=speed_kmh,
        timestamp_sec=1.0,
        world_x=0.0,
        world_y=0.0,
        physics_valid=physics_valid,
        innovation_nis=nis,
        adaptive_measurement_noise_multiplier=multiplier,
    )


def test_nis_diagnostics_marks_insufficient_samples() -> None:
    summary = NISDiagnosticsAnalyzer(min_sample_count=4).analyze(
        [_record(2.0), _record(None), _record(1.8, physics_valid=False)]
    )

    assert summary.sample_count == 1
    assert summary.consistency_label == "insufficient_samples"
    assert summary.model_reference == "nis_consistency_diagnostics_v1"


def test_nis_diagnostics_marks_well_calibrated_near_target() -> None:
    summary = NISDiagnosticsAnalyzer(min_sample_count=4).analyze(
        [_record(value) for value in [1.5, 1.9, 2.1, 2.4, 3.0]]
    )

    assert summary.consistency_label == "well_calibrated"
    assert summary.mean_nis > 0.0
    assert summary.high_nis_ratio == 0.0


def test_nis_diagnostics_marks_high_nis_as_underestimated_noise() -> None:
    summary = NISDiagnosticsAnalyzer(min_sample_count=4).analyze(
        [_record(value) for value in [6.5, 7.0, 8.0, 9.0, 2.0]]
    )

    assert summary.consistency_label == "underestimated_measurement_noise"
    assert summary.high_nis_ratio > 0.5
    assert "increase" in summary.recommendation


def test_nis_diagnostics_marks_low_nis_as_overestimated_noise() -> None:
    summary = NISDiagnosticsAnalyzer(min_sample_count=4).analyze(
        [_record(value) for value in [0.01, 0.05, 0.08, 0.1, 1.0]]
    )

    assert summary.consistency_label == "overestimated_measurement_noise"
    assert summary.low_nis_ratio > 0.5
    assert "decrease" in summary.recommendation


def test_nis_diagnostics_ignores_empty_invalid_and_missing_nis_records() -> None:
    summary = NISDiagnosticsAnalyzer(min_sample_count=1).analyze(
        [
            _record(None),
            _record(8.0, physics_valid=False),
            _record(9.0, speed_kmh=None),
            _record(2.0, multiplier=1.4),
        ]
    )

    assert summary.sample_count == 1
    assert summary.mean_nis == 2.0
    assert summary.mean_adaptive_multiplier == 1.4
