from __future__ import annotations

from statistics import mean, pstdev


def min_displacement_filter(displacement_m: float, threshold: float) -> float:
    return 0.0 if displacement_m < threshold else displacement_m


def max_speed_filter(speed_kmh: float, max_speed: float) -> float | None:
    return None if speed_kmh > max_speed else speed_kmh


def statistical_outlier_filter(speeds: list[float], sigma: float = 3.0) -> list[float]:
    if len(speeds) < 2:
        return speeds
    avg = mean(speeds)
    deviation = pstdev(speeds)
    if deviation == 0:
        return speeds
    return [speed for speed in speeds if abs(speed - avg) <= sigma * deviation]
