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
