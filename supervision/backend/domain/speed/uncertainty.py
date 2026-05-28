from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SpeedUncertainty:
    speed_uncertainty_kmh: float
    speed_confidence: float
    position_rmse_m: float


def estimate_speed_uncertainty(
    displacement_m: float,
    delta_t_sec: float,
    position_rmse_m: float,
    timestamp_uncertainty_sec: float = 0.0,
) -> SpeedUncertainty:
    if delta_t_sec <= 0:
        raise ValueError("delta_t_sec must be positive")
    if displacement_m < 0:
        raise ValueError("displacement_m must not be negative")
    if position_rmse_m < 0:
        raise ValueError("position_rmse_m must not be negative")
    if timestamp_uncertainty_sec < 0:
        raise ValueError("timestamp_uncertainty_sec must not be negative")

    denominator = max(displacement_m, 1e-6)
    relative_distance_error = position_rmse_m / denominator
    relative_time_error = timestamp_uncertainty_sec / delta_t_sec
    nominal_speed_kmh = displacement_m / delta_t_sec * 3.6
    relative_error = (relative_distance_error**2 + relative_time_error**2) ** 0.5
    position_uncertainty_kmh = position_rmse_m / delta_t_sec * 3.6
    time_uncertainty_kmh = nominal_speed_kmh * relative_time_error
    uncertainty_kmh = (
        position_uncertainty_kmh * (1.0 + relative_distance_error) + time_uncertainty_kmh
    )
    confidence = 1.0 / (1.0 + relative_error)

    return SpeedUncertainty(
        speed_uncertainty_kmh=float(uncertainty_kmh),
        speed_confidence=float(max(0.0, min(1.0, confidence))),
        position_rmse_m=float(position_rmse_m),
    )
