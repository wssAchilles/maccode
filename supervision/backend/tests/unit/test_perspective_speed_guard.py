from __future__ import annotations

from domain.speed.perspective_guard import (
    PerspectiveGuardSample,
    PerspectiveSpeedInflationDetector,
)


def test_constant_speed_with_stable_local_scale_does_not_trigger_guard() -> None:
    samples = [
        PerspectiveGuardSample(
            speed_kmh=5.0,
            pixel_y=float(index),
            local_scale_factor=1.1,
            local_scale_percentile=0.4,
            timestamp_sec=float(index),
        )
        for index in range(6)
    ]

    result = PerspectiveSpeedInflationDetector().analyze(
        samples,
        max_speed_kmh=18.0,
    )

    assert result.perspective_speed_inflation_detected is False
    assert result.geometry_rejection_reason is None


def test_speed_increasing_with_local_scale_triggers_guard() -> None:
    samples = [
        PerspectiveGuardSample(
            speed_kmh=speed,
            pixel_y=float(index),
            local_scale_factor=scale,
            local_scale_percentile=0.9,
            timestamp_sec=float(index),
        )
        for index, (speed, scale) in enumerate(
            [(5.0, 1.0), (7.0, 1.3), (10.0, 1.6), (15.0, 2.0), (24.0, 2.5)]
        )
    ]

    result = PerspectiveSpeedInflationDetector().analyze(
        samples,
        max_speed_kmh=18.0,
    )

    assert result.perspective_speed_inflation_detected is True
    assert result.speed_scale_correlation is not None
    assert result.speed_scale_correlation >= 0.65
    assert result.geometry_rejection_reason == "perspective_speed_inflation"


def test_far_near_speed_ratio_triggers_guard() -> None:
    samples = [
        PerspectiveGuardSample(6.0, 0.0, 1.0, 0.2, 0.0),
        PerspectiveGuardSample(6.2, 1.0, 1.1, 0.3, 1.0),
        PerspectiveGuardSample(12.5, 2.0, 1.2, 0.7, 2.0),
        PerspectiveGuardSample(13.0, 3.0, 1.3, 0.8, 3.0),
        PerspectiveGuardSample(14.0, 4.0, 1.4, 0.9, 4.0),
    ]

    result = PerspectiveSpeedInflationDetector().analyze(
        samples,
        max_speed_kmh=18.0,
    )

    assert result.perspective_speed_inflation_detected is True
    assert result.far_near_speed_ratio is not None
    assert result.far_near_speed_ratio >= 2.0


def test_insufficient_samples_only_reports_model_reference() -> None:
    result = PerspectiveSpeedInflationDetector().analyze(
        [
            PerspectiveGuardSample(20.0, 0.0, 3.0, 0.95, 0.0),
            PerspectiveGuardSample(22.0, 1.0, 4.0, 0.96, 1.0),
        ],
        max_speed_kmh=18.0,
    )

    assert result.perspective_speed_inflation_detected is False
    assert result.geometry_rejection_reason is None
    assert result.model_reference == "pedestrian_perspective_speed_guard_v1"


def test_far_field_high_speed_triggers_direct_rejection() -> None:
    samples = [
        PerspectiveGuardSample(
            speed_kmh=22.0,
            pixel_y=float(index),
            local_scale_factor=3.0,
            local_scale_percentile=0.96,
            timestamp_sec=float(index),
        )
        for index in range(5)
    ]

    result = PerspectiveSpeedInflationDetector().analyze(
        samples,
        max_speed_kmh=18.0,
    )

    assert result.perspective_speed_inflation_detected is True
    assert result.geometry_rejection_reason == "perspective_speed_inflation"
