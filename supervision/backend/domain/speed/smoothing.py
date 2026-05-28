from __future__ import annotations

from statistics import mean, median


def median_smoothing(values: list[float], window_size: int) -> float:
    if not values:
        raise ValueError("values must not be empty")
    window = values[-window_size:]
    return float(median(window))


def exponential_smoothing(values: list[float], alpha: float) -> float:
    if not values:
        raise ValueError("values must not be empty")
    if not 0.0 < alpha <= 1.0:
        raise ValueError("alpha must be in (0, 1]")
    smoothed = values[0]
    for value in values[1:]:
        smoothed = alpha * value + (1.0 - alpha) * smoothed
    return float(smoothed)


def moving_average(values: list[float], window_size: int) -> float:
    if not values:
        raise ValueError("values must not be empty")
    return float(mean(values[-window_size:]))
