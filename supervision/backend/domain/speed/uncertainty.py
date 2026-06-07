from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SpeedUncertainty:
    speed_uncertainty_kmh: float
    speed_confidence: float
    position_rmse_m: float
    was_capped: bool = False


def estimate_speed_uncertainty(
    displacement_m: float,
    delta_t_sec: float,
    position_rmse_m: float,
    timestamp_uncertainty_sec: float = 0.0,
    residual_m: float = 0.0,
    detection_confidence: float = 1.0,
    measurement_confidence: float = 1.0,
    local_scale_factor: float = 1.0,
    position_sigma_m: float | None = None,
    calibration_rmse_m: float | None = None,
    scale_uncertainty_factor: float = 0.0,
    track_age_frames: int | None = None,
    min_track_age_frames: int | None = None,
    uncertainty_cap_kmh: float | None = None,
) -> SpeedUncertainty:
    if delta_t_sec <= 0:
        raise ValueError("delta_t_sec must be positive")
    if displacement_m < 0:
        raise ValueError("displacement_m must not be negative")
    if position_rmse_m < 0:
        raise ValueError("position_rmse_m must not be negative")
    if timestamp_uncertainty_sec < 0:
        raise ValueError("timestamp_uncertainty_sec must not be negative")
    if residual_m < 0:
        raise ValueError("residual_m must not be negative")
    if measurement_confidence < 0:
        raise ValueError("measurement_confidence must not be negative")
    if local_scale_factor <= 0:
        raise ValueError("local_scale_factor must be positive")
    if position_sigma_m is not None and position_sigma_m < 0:
        raise ValueError("position_sigma_m must not be negative")
    if calibration_rmse_m is not None and calibration_rmse_m < 0:
        raise ValueError("calibration_rmse_m must not be negative")
    if scale_uncertainty_factor < 0:
        raise ValueError("scale_uncertainty_factor must not be negative")

    denominator = max(displacement_m, 1e-6)
    bounded_measurement_confidence = max(0.05, min(1.0, measurement_confidence))
    scaled_rmse_m = position_sigma_m if position_sigma_m is not None else (
        position_rmse_m * local_scale_factor
    )
    scaled_rmse_m = scaled_rmse_m / bounded_measurement_confidence**0.5
    calibration_error_m = calibration_rmse_m or 0.0
    scale_error_m = denominator * scale_uncertainty_factor * max(
        local_scale_factor - 1.0,
        0.0,
    )
    effective_position_error_m = (
        scaled_rmse_m**2
        + residual_m**2
        + calibration_error_m**2
        + scale_error_m**2
    ) ** 0.5
    relative_distance_error = effective_position_error_m / denominator
    relative_time_error = timestamp_uncertainty_sec / delta_t_sec
    nominal_speed_kmh = displacement_m / delta_t_sec * 3.6
    relative_error = (relative_distance_error**2 + relative_time_error**2) ** 0.5
    position_uncertainty_kmh = effective_position_error_m / delta_t_sec * 3.6
    time_uncertainty_kmh = nominal_speed_kmh * relative_time_error
    bounded_distance_factor = 1.0 + min(relative_distance_error, 1.0)
    raw_uncertainty_kmh = (
        position_uncertainty_kmh * bounded_distance_factor + time_uncertainty_kmh
    )
    was_capped = uncertainty_cap_kmh is not None and raw_uncertainty_kmh > uncertainty_cap_kmh
    uncertainty_kmh = (
        min(raw_uncertainty_kmh, uncertainty_cap_kmh)
        if uncertainty_cap_kmh is not None
        else raw_uncertainty_kmh
    )
    detection_factor = max(0.0, min(1.0, detection_confidence))
    measurement_factor = bounded_measurement_confidence
    age_factor = 1.0
    if track_age_frames is not None and min_track_age_frames is not None:
        age_factor = max(0.0, min(1.0, track_age_frames / max(min_track_age_frames, 1)))
    cap_factor = 0.35 if was_capped else 1.0
    confidence = (
        (1.0 / (1.0 + relative_error))
        * detection_factor
        * measurement_factor
        * age_factor
        * cap_factor
    )

    return SpeedUncertainty(
        speed_uncertainty_kmh=float(uncertainty_kmh),
        speed_confidence=float(max(0.0, min(1.0, confidence))),
        position_rmse_m=float(scaled_rmse_m),
        was_capped=was_capped,
    )
