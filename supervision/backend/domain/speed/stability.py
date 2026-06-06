from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class SpeedStabilityMetrics:
    speed_stability_score: float
    speed_cv: float | None
    max_speed_jump_kmh: float | None
    speed_jump_p95_kmh: float | None
    acceleration_p95_mps2: float | None
    jerk_p95_mps3: float | None
    stability_label: str


def compute_speed_stability(
    timestamps_sec: list[float],
    speeds_kmh: list[float | None],
    accelerations_mps2: list[float | None] | None = None,
) -> SpeedStabilityMetrics:
    valid_pairs = [
        (timestamp, speed)
        for timestamp, speed in zip(timestamps_sec, speeds_kmh, strict=False)
        if speed is not None and np.isfinite(speed)
    ]
    if len(valid_pairs) < 3:
        return SpeedStabilityMetrics(
            speed_stability_score=0.0,
            speed_cv=None,
            max_speed_jump_kmh=None,
            speed_jump_p95_kmh=None,
            acceleration_p95_mps2=None,
            jerk_p95_mps3=None,
            stability_label="insufficient_samples",
        )

    valid_timestamps = np.array([pair[0] for pair in valid_pairs], dtype=np.float64)
    valid_speeds = np.array([pair[1] for pair in valid_pairs], dtype=np.float64)
    mean_speed = float(np.mean(valid_speeds))
    speed_std = float(np.std(valid_speeds))
    speed_cv = speed_std / max(abs(mean_speed), 1.0)
    speed_jumps = np.abs(np.diff(valid_speeds))
    max_speed_jump = float(np.max(speed_jumps)) if speed_jumps.size else 0.0
    speed_jump_p95 = _p95_abs(speed_jumps)

    if accelerations_mps2 is None:
        speed_mps = valid_speeds / 3.6
        delta_t = np.diff(valid_timestamps)
        valid_delta = delta_t > 1e-6
        acceleration_values = np.diff(speed_mps)[valid_delta] / delta_t[valid_delta]
    else:
        acceleration_values = np.array(
            [
                value
                for value in accelerations_mps2
                if value is not None and np.isfinite(value)
            ],
            dtype=np.float64,
        )
    acceleration_p95 = _p95_abs(acceleration_values)

    if acceleration_values.size >= 2:
        accel_timestamps = valid_timestamps[-acceleration_values.size :]
        delta_t = np.diff(accel_timestamps)
        valid_delta = delta_t > 1e-6
        jerk_values = np.diff(acceleration_values)[valid_delta] / delta_t[valid_delta]
    else:
        jerk_values = np.array([], dtype=np.float64)
    jerk_p95 = _p95_abs(jerk_values)

    cv_penalty = min(speed_cv / 0.35, 1.0)
    jump_penalty = min(max_speed_jump / max(abs(mean_speed) * 0.7, 3.0), 1.0)
    accel_penalty = min((acceleration_p95 or 0.0) / 8.0, 1.0)
    score = max(0.0, min(1.0, 1.0 - 0.55 * cv_penalty - 0.3 * jump_penalty - 0.15 * accel_penalty))
    if score >= 0.78:
        label = "stable"
    elif score >= 0.48:
        label = "variable"
    else:
        label = "unstable_observation"

    return SpeedStabilityMetrics(
        speed_stability_score=float(score),
        speed_cv=float(speed_cv),
        max_speed_jump_kmh=float(max_speed_jump),
        speed_jump_p95_kmh=speed_jump_p95,
        acceleration_p95_mps2=acceleration_p95,
        jerk_p95_mps3=jerk_p95,
        stability_label=label,
    )


def _p95_abs(values: np.ndarray) -> float | None:
    if values.size == 0:
        return None
    return float(np.percentile(np.abs(values), 95))
