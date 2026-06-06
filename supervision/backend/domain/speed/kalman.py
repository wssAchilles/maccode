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
    acceleration_mps2: float | None = None


@dataclass(frozen=True)
class KalmanMeasurementPrediction:
    predicted_position: tuple[float, float]
    innovation: NDArray[np.float64]
    innovation_covariance: NDArray[np.float64]
    mahalanobis_d2: float
    covariance_solver: str
    confidence_penalty: float = 0.0


class KalmanFilter2D:
    def __init__(self, config: KalmanConfig) -> None:
        self.config = config
        self._state: NDArray[np.float64] | None = None
        self._covariance: NDArray[np.float64] | None = None
        self._last_timestamp: float | None = None
        self._last_measurement: tuple[float, float] | None = None

    @property
    def state(self) -> KalmanState | None:
        if self._state is None or self._covariance is None:
            return None
        return self._to_state()

    def update(
        self,
        position: tuple[float, float],
        timestamp_sec: float,
        measurement_noise: float | None = None,
    ) -> KalmanState:
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

        transition = self._transition_matrix(delta_t)
        process_noise = self._process_noise_matrix(delta_t)
        predicted_state = transition @ self._state
        predicted_covariance = transition @ self._covariance @ transition.T + process_noise

        observation = self._observation_matrix()
        measurement_noise_matrix = self._measurement_noise_matrix(measurement_noise)
        innovation = measurement - observation @ predicted_state
        innovation_covariance = (
            observation @ predicted_covariance @ observation.T + measurement_noise_matrix
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

    def predict_measurement(
        self,
        position: tuple[float, float],
        timestamp_sec: float,
        measurement_noise: float | None = None,
    ) -> KalmanMeasurementPrediction:
        measurement = np.array([[position[0]], [position[1]]], dtype=float)
        observation = self._observation_matrix()
        if self._state is None or self._covariance is None or self._last_timestamp is None:
            innovation_covariance = (
                np.eye(2, dtype=float)
                * (
                    self.config.initial_position_variance
                    + self._measurement_noise_value(measurement_noise)
                )
            )
            return KalmanMeasurementPrediction(
                predicted_position=position,
                innovation=np.zeros((2, 1), dtype=np.float64),
                innovation_covariance=innovation_covariance,
                mahalanobis_d2=0.0,
                covariance_solver="uninitialized",
            )
        delta_t = timestamp_sec - self._last_timestamp
        if delta_t <= 0:
            predicted_position = observation @ self._state
            innovation_covariance = (
                observation @ self._covariance @ observation.T
                + self._measurement_noise_matrix(measurement_noise)
            )
            innovation = measurement - predicted_position
            mahalanobis_d2, solver, penalty = self._mahalanobis_d2(
                innovation,
                innovation_covariance,
            )
            return KalmanMeasurementPrediction(
                predicted_position=(
                    float(predicted_position[0, 0]),
                    float(predicted_position[1, 0]),
                ),
                innovation=innovation.astype(np.float64),
                innovation_covariance=innovation_covariance.astype(np.float64),
                mahalanobis_d2=mahalanobis_d2,
                covariance_solver=solver,
                confidence_penalty=penalty,
            )
        transition = self._transition_matrix(delta_t)
        predicted_state = transition @ self._state
        predicted_covariance = (
            transition @ self._covariance @ transition.T + self._process_noise_matrix(delta_t)
        )
        predicted_position = observation @ predicted_state
        innovation = measurement - predicted_position
        innovation_covariance = (
            observation @ predicted_covariance @ observation.T
            + self._measurement_noise_matrix(measurement_noise)
        )
        mahalanobis_d2, solver, penalty = self._mahalanobis_d2(
            innovation,
            innovation_covariance,
        )
        return KalmanMeasurementPrediction(
            predicted_position=(
                float(predicted_position[0, 0]),
                float(predicted_position[1, 0]),
            ),
            innovation=innovation.astype(np.float64),
            innovation_covariance=innovation_covariance.astype(np.float64),
            mahalanobis_d2=mahalanobis_d2,
            covariance_solver=solver,
            confidence_penalty=penalty,
        )

    @staticmethod
    def _transition_matrix(delta_t: float) -> NDArray[np.float64]:
        return np.array(
            [
                [1.0, 0.0, delta_t, 0.0],
                [0.0, 1.0, 0.0, delta_t],
                [0.0, 0.0, 1.0, 0.0],
                [0.0, 0.0, 0.0, 1.0],
            ],
            dtype=np.float64,
        )

    @staticmethod
    def _observation_matrix() -> NDArray[np.float64]:
        return np.array(
            [[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0]],
            dtype=np.float64,
        )

    def _measurement_noise_matrix(
        self,
        measurement_noise: float | None = None,
    ) -> NDArray[np.float64]:
        return np.eye(2, dtype=np.float64) * self._measurement_noise_value(measurement_noise)

    def _measurement_noise_value(self, measurement_noise: float | None = None) -> float:
        if measurement_noise is None:
            return float(self.config.measurement_noise)
        return float(max(measurement_noise, 1e-6))

    @staticmethod
    def _mahalanobis_d2(
        innovation: NDArray[np.float64],
        innovation_covariance: NDArray[np.float64],
    ) -> tuple[float, str, float]:
        penalty = 0.0
        solver = "solve"
        try:
            if np.linalg.cond(innovation_covariance) > 1e10:
                raise np.linalg.LinAlgError("ill-conditioned innovation covariance")
            solved = np.linalg.solve(innovation_covariance, innovation)
        except np.linalg.LinAlgError:
            penalty = 0.15
            solver = "jittered_solve"
            jittered = innovation_covariance + np.eye(2, dtype=np.float64) * 1e-6
            try:
                solved = np.linalg.solve(jittered, innovation)
            except np.linalg.LinAlgError:
                penalty = 0.3
                solver = "pinv"
                solved = np.linalg.pinv(jittered) @ innovation
        value = float((innovation.T @ solved)[0, 0])
        return max(0.0, value), solver, penalty

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


class ConstantAccelerationKalmanFilter2D:
    def __init__(self, config: KalmanConfig) -> None:
        self.config = config
        self._state: NDArray[np.float64] | None = None
        self._covariance: NDArray[np.float64] | None = None
        self._last_timestamp: float | None = None

    @property
    def state(self) -> KalmanState | None:
        if self._state is None or self._covariance is None:
            return None
        return self._to_state()

    def update(
        self,
        position: tuple[float, float],
        timestamp_sec: float,
        measurement_noise: float | None = None,
    ) -> KalmanState:
        measurement = np.array([[position[0]], [position[1]]], dtype=np.float64)
        if self._state is None:
            self._state = np.array(
                [[position[0]], [position[1]], [0.0], [0.0], [0.0], [0.0]],
                dtype=np.float64,
            )
            self._covariance = np.diag([10.0, 10.0, 10.0, 10.0, 4.0, 4.0]).astype(
                np.float64
            )
            self._last_timestamp = timestamp_sec
            return self._to_state()
        if self._last_timestamp is None or self._covariance is None:
            raise RuntimeError("constant acceleration filter was not initialized correctly")
        delta_t = timestamp_sec - self._last_timestamp
        if delta_t <= 0:
            return self._to_state()

        transition = self._transition_matrix(delta_t)
        predicted_state = transition @ self._state
        predicted_covariance = (
            transition @ self._covariance @ transition.T
            + self._process_noise_matrix(delta_t)
        )
        observation = self._observation_matrix()
        measurement_covariance = np.eye(2, dtype=np.float64) * self._measurement_noise_value(
            measurement_noise
        )
        innovation = measurement - observation @ predicted_state
        innovation_covariance = (
            observation @ predicted_covariance @ observation.T + measurement_covariance
        )
        kalman_gain = predicted_covariance @ observation.T @ np.linalg.pinv(
            innovation_covariance
        )
        self._state = predicted_state + kalman_gain @ innovation
        self._covariance = (
            np.eye(6, dtype=np.float64) - kalman_gain @ observation
        ) @ predicted_covariance
        self._last_timestamp = timestamp_sec
        return self._to_state()

    def predict_measurement(
        self,
        position: tuple[float, float],
        timestamp_sec: float,
        measurement_noise: float | None = None,
    ) -> KalmanMeasurementPrediction:
        measurement = np.array([[position[0]], [position[1]]], dtype=np.float64)
        observation = self._observation_matrix()
        if self._state is None or self._covariance is None or self._last_timestamp is None:
            covariance = np.eye(2, dtype=np.float64) * (
                self.config.initial_position_variance
                + self._measurement_noise_value(measurement_noise)
            )
            return KalmanMeasurementPrediction(
                predicted_position=position,
                innovation=np.zeros((2, 1), dtype=np.float64),
                innovation_covariance=covariance,
                mahalanobis_d2=0.0,
                covariance_solver="uninitialized",
            )
        delta_t = max(timestamp_sec - self._last_timestamp, 0.0)
        transition = self._transition_matrix(delta_t)
        predicted_state = transition @ self._state
        predicted_covariance = (
            transition @ self._covariance @ transition.T
            + self._process_noise_matrix(delta_t)
        )
        predicted_position = observation @ predicted_state
        innovation = measurement - predicted_position
        innovation_covariance = (
            observation @ predicted_covariance @ observation.T
            + np.eye(2, dtype=np.float64) * self._measurement_noise_value(measurement_noise)
        )
        mahalanobis_d2, solver, penalty = KalmanFilter2D._mahalanobis_d2(
            innovation,
            innovation_covariance,
        )
        return KalmanMeasurementPrediction(
            predicted_position=(
                float(predicted_position[0, 0]),
                float(predicted_position[1, 0]),
            ),
            innovation=innovation,
            innovation_covariance=innovation_covariance,
            mahalanobis_d2=mahalanobis_d2,
            covariance_solver=solver,
            confidence_penalty=penalty,
        )

    @staticmethod
    def _transition_matrix(delta_t: float) -> NDArray[np.float64]:
        half_dt2 = 0.5 * delta_t**2
        return np.array(
            [
                [1.0, 0.0, delta_t, 0.0, half_dt2, 0.0],
                [0.0, 1.0, 0.0, delta_t, 0.0, half_dt2],
                [0.0, 0.0, 1.0, 0.0, delta_t, 0.0],
                [0.0, 0.0, 0.0, 1.0, 0.0, delta_t],
                [0.0, 0.0, 0.0, 0.0, 1.0, 0.0],
                [0.0, 0.0, 0.0, 0.0, 0.0, 1.0],
            ],
            dtype=np.float64,
        )

    @staticmethod
    def _observation_matrix() -> NDArray[np.float64]:
        return np.array(
            [[1.0, 0.0, 0.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0, 0.0, 0.0]],
            dtype=np.float64,
        )

    def _process_noise_matrix(self, delta_t: float) -> NDArray[np.float64]:
        q = self.config.process_noise
        return np.diag(
            [
                delta_t**4 / 4.0,
                delta_t**4 / 4.0,
                delta_t**2,
                delta_t**2,
                max(delta_t, 1e-3),
                max(delta_t, 1e-3),
            ]
        ).astype(np.float64) * q

    def _measurement_noise_value(self, measurement_noise: float | None = None) -> float:
        if measurement_noise is None:
            return float(self.config.measurement_noise)
        return float(max(measurement_noise, 1e-6))

    def _to_state(self) -> KalmanState:
        if self._state is None or self._covariance is None:
            raise RuntimeError("constant acceleration filter has no state")
        vx = float(self._state[2, 0])
        vy = float(self._state[3, 0])
        ax = float(self._state[4, 0])
        ay = float(self._state[5, 0])
        speed_kmh = (vx**2 + vy**2) ** 0.5 * 3.6
        velocity_variance = max(float(self._covariance[2, 2] + self._covariance[3, 3]), 0.0)
        speed_confidence = 1.0 / (1.0 + 0.5 * velocity_variance**0.5)
        return KalmanState(
            position=(float(self._state[0, 0]), float(self._state[1, 0])),
            velocity_mps=(vx, vy),
            speed_kmh=float(speed_kmh),
            covariance=self._covariance.copy(),
            speed_confidence=float(max(0.0, min(1.0, speed_confidence))),
            acceleration_mps2=float((ax**2 + ay**2) ** 0.5),
        )


def kalman_config_for_motion_profile(process_noise: str) -> KalmanConfig:
    if process_noise == "low":
        return KalmanConfig(process_noise=0.05, measurement_noise=0.25)
    if process_noise == "high":
        return KalmanConfig(process_noise=4.0, measurement_noise=0.15)
    return KalmanConfig(process_noise=0.5, measurement_noise=0.25)
