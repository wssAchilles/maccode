from __future__ import annotations

from domain.speed.imm import LightweightIMMEstimator


def test_imm_prefers_constant_velocity_on_uniform_motion() -> None:
    states = LightweightIMMEstimator().estimate(
        [0.0, 1.0, 2.0, 3.0],
        [0.0, 10.0, 20.0, 30.0],
        [0.0, 0.0, 0.0, 0.0],
    )

    assert states[-1].motion_mode == "constant_velocity"
    assert states[-1].imm_speed_kmh > 0.0


def test_imm_marks_near_stop_when_track_is_stationary() -> None:
    states = LightweightIMMEstimator().estimate(
        [0.0, 1.0, 2.0, 3.0],
        [5.0, 5.0, 5.0, 5.0],
        [2.0, 2.0, 2.0, 2.0],
    )

    assert states[-1].motion_mode == "near_stop"
    assert states[-1].motion_mode_probability > 0.4
