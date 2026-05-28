from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True)
class KalmanConfig:
    process_noise: float
    measurement_noise: float
    initial_position_variance: float = 10.0
    initial_velocity_variance: float = 10.0


@dataclass(frozen=True)
class KalmanState:
    position: tuple[float, float]
    velocity_mps: tuple[float, float]
    speed_kmh: float
    covariance: NDArray[np.float64]
    speed_confidence: float


class KalmanFilter2D:
    def __init__(self, config: KalmanConfig) -> None:
        self.config = config
        self._state: NDArray[np.float64] | None = None
        self._covariance: NDArray[np.float64] | None = None
        self._last_timestamp: float | None = None
        self._last_measurement: tuple[float, float] | None = None

    def update(self, position: tuple[float, float], timestamp_sec: float) -> KalmanState:
        measurement = np.array([[position[0]], [position[1]]], dtype=float)
        if self._state is None:
            self._state = np.array([[position[0]], [position[1]], [0.0], [0.0]], dtype=float)
            self._covariance = np.diag(
                [
                    self.config.initial_position_variance,
                    self.config.initial_position_variance,
                    self.config.initial_velocity_variance,
                    self.config.initial_velocity_variance,
                ]
            ).astype(np.float64)
            self._last_timestamp = timestamp_sec
            self._last_measurement = position
            return self._to_state()

        if self._last_timestamp is None or self._covariance is None:
            raise RuntimeError("kalman filter was not initialized correctly")

        delta_t = timestamp_sec - self._last_timestamp
        if delta_t <= 0:
            return self._to_state()

        transition = np.array(
            [
                [1.0, 0.0, delta_t, 0.0],
                [0.0, 1.0, 0.0, delta_t],
                [0.0, 0.0, 1.0, 0.0],
                [0.0, 0.0, 0.0, 1.0],
            ],
            dtype=float,
        )
        process_noise = self._process_noise_matrix(delta_t)
        predicted_state = transition @ self._state
        predicted_covariance = transition @ self._covariance @ transition.T + process_noise

        observation = np.array([[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0]], dtype=float)
        measurement_noise = np.eye(2, dtype=float) * self.config.measurement_noise
        innovation = measurement - observation @ predicted_state
        innovation_covariance = (
            observation @ predicted_covariance @ observation.T + measurement_noise
        )
        kalman_gain = predicted_covariance @ observation.T @ np.linalg.inv(innovation_covariance)

        self._state = predicted_state + kalman_gain @ innovation
        identity = np.eye(4, dtype=float)
        self._covariance = (identity - kalman_gain @ observation) @ predicted_covariance
        if self._last_measurement is not None:
            measured_velocity = (
                (position[0] - self._last_measurement[0]) / delta_t,
                (position[1] - self._last_measurement[1]) / delta_t,
            )
            blend = min(0.95, self.config.process_noise / (self.config.process_noise + 1.0))
            self._state[2, 0] = (1.0 - blend) * self._state[2, 0] + blend * measured_velocity[0]
            self._state[3, 0] = (1.0 - blend) * self._state[3, 0] + blend * measured_velocity[1]
        self._last_timestamp = timestamp_sec
        self._last_measurement = position
        return self._to_state()

    def _process_noise_matrix(self, delta_t: float) -> NDArray[np.float64]:
        dt2 = delta_t**2
        dt3 = delta_t**3
        dt4 = delta_t**4
        q = self.config.process_noise
        return np.array(
            [
                [dt4 / 4.0, 0.0, dt3 / 2.0, 0.0],
                [0.0, dt4 / 4.0, 0.0, dt3 / 2.0],
                [dt3 / 2.0, 0.0, dt2, 0.0],
                [0.0, dt3 / 2.0, 0.0, dt2],
            ],
            dtype=float,
        ) * q

    def _to_state(self) -> KalmanState:
        if self._state is None or self._covariance is None:
            raise RuntimeError("kalman filter has no state")
        vx = float(self._state[2, 0])
        vy = float(self._state[3, 0])
        speed_kmh = (vx**2 + vy**2) ** 0.5 * 3.6
        velocity_variance = max(float(self._covariance[2, 2] + self._covariance[3, 3]), 0.0)
        speed_confidence = 1.0 / (1.0 + 0.5 * velocity_variance**0.5)
        return KalmanState(
            position=(float(self._state[0, 0]), float(self._state[1, 0])),
            velocity_mps=(vx, vy),
            speed_kmh=float(speed_kmh),
            covariance=self._covariance.copy(),
            speed_confidence=float(max(0.0, min(1.0, speed_confidence))),
        )


def kalman_config_for_motion_profile(process_noise: str) -> KalmanConfig:
    if process_noise == "low":
        return KalmanConfig(process_noise=0.05, measurement_noise=0.25)
    if process_noise == "high":
        return KalmanConfig(process_noise=4.0, measurement_noise=0.15)
    return KalmanConfig(process_noise=0.5, measurement_noise=0.25)
