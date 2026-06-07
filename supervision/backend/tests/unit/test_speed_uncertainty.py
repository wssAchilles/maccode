from __future__ import annotations

import pytest
from domain.speed.uncertainty import estimate_speed_uncertainty


def test_short_displacement_has_higher_speed_uncertainty() -> None:
    short = estimate_speed_uncertainty(
        displacement_m=0.2,
        delta_t_sec=1.0,
        position_rmse_m=0.15,
        timestamp_uncertainty_sec=0.01,
    )
    long = estimate_speed_uncertainty(
        displacement_m=5.0,
        delta_t_sec=1.0,
        position_rmse_m=0.15,
        timestamp_uncertainty_sec=0.01,
    )

    assert short.speed_uncertainty_kmh > long.speed_uncertainty_kmh
    assert short.speed_confidence < long.speed_confidence


def test_speed_confidence_degrades_with_large_position_rmse() -> None:
    clean = estimate_speed_uncertainty(4.0, 1.0, position_rmse_m=0.05)
    noisy = estimate_speed_uncertainty(4.0, 1.0, position_rmse_m=1.0)

    assert clean.speed_confidence > 0.9
    assert noisy.speed_confidence < clean.speed_confidence
    assert noisy.position_rmse_m == pytest.approx(1.0)


def test_measurement_confidence_and_local_scale_increase_uncertainty() -> None:
    baseline = estimate_speed_uncertainty(
        displacement_m=4.0,
        delta_t_sec=1.0,
        position_rmse_m=0.1,
        measurement_confidence=1.0,
        local_scale_factor=1.0,
    )
    weak_far_observation = estimate_speed_uncertainty(
        displacement_m=4.0,
        delta_t_sec=1.0,
        position_rmse_m=0.1,
        measurement_confidence=0.35,
        local_scale_factor=3.0,
    )

    assert weak_far_observation.speed_uncertainty_kmh > baseline.speed_uncertainty_kmh
    assert weak_far_observation.speed_confidence < baseline.speed_confidence
    assert weak_far_observation.position_rmse_m > baseline.position_rmse_m


def test_calibration_and_scale_uncertainty_increase_speed_uncertainty() -> None:
    baseline = estimate_speed_uncertainty(
        displacement_m=4.0,
        delta_t_sec=1.0,
        position_rmse_m=0.1,
        local_scale_factor=1.0,
    )
    weak_geometry = estimate_speed_uncertainty(
        displacement_m=4.0,
        delta_t_sec=1.0,
        position_rmse_m=0.1,
        local_scale_factor=4.0,
        calibration_rmse_m=0.8,
        scale_uncertainty_factor=0.05,
    )

    assert weak_geometry.speed_uncertainty_kmh > baseline.speed_uncertainty_kmh
    assert weak_geometry.speed_confidence < baseline.speed_confidence
