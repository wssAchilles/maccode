from __future__ import annotations

import pytest
from domain.speed.adaptive_noise import AdaptiveMeasurementNoiseController


def test_stable_nis_keeps_multiplier_near_one() -> None:
    controller = AdaptiveMeasurementNoiseController()

    for _ in range(10):
        state = controller.update(2.0)

    assert state.multiplier == pytest.approx(1.0, abs=0.05)
    assert state.accepted_sample_count == 10


def test_repeated_high_nis_increases_multiplier() -> None:
    controller = AdaptiveMeasurementNoiseController()

    for _ in range(8):
        state = controller.update(8.0)

    assert state.multiplier > 1.5
    assert state.ewma_nis > controller.target_nis


def test_extreme_nis_is_not_used_for_learning() -> None:
    controller = AdaptiveMeasurementNoiseController()
    before = controller.update(2.0)
    after = controller.update(40.0)

    assert after.multiplier == before.multiplier
    assert after.ewma_nis == before.ewma_nis
    assert after.accepted_sample_count == before.accepted_sample_count
    assert after.skipped_outlier_count == 1


def test_low_nis_reduces_multiplier_without_crossing_floor() -> None:
    controller = AdaptiveMeasurementNoiseController()

    for _ in range(30):
        state = controller.update(0.1)

    assert 0.5 <= state.multiplier < 1.0
