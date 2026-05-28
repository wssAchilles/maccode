from __future__ import annotations

import math

from shared.configs.constants import DEFAULT_MAX_SPEED_KMH, DEFAULT_MIN_DISPLACEMENT_M

from domain.speed.filters import max_speed_filter, min_displacement_filter
from domain.speed.kalman import KalmanFilter2D, kalman_config_for_motion_profile
from domain.speed.models import SpeedRecord, TrackHistory
from domain.speed.smoothing import median_smoothing
from domain.speed.uncertainty import estimate_speed_uncertainty
from domain.speed.view_transformer import ViewTransformer


class SpeedEstimator:
    def __init__(
        self,
        view_transformer: ViewTransformer,
        smoothing_window: int = 5,
        min_displacement_m: float = DEFAULT_MIN_DISPLACEMENT_M,
        max_speed_kmh: float = DEFAULT_MAX_SPEED_KMH,
        position_rmse_m: float = 0.1,
        timestamp_uncertainty_sec: float = 0.0,
    ) -> None:
        self.view_transformer = view_transformer
        self.smoothing_window = smoothing_window
        self.min_displacement_m = min_displacement_m
        self.max_speed_kmh = max_speed_kmh
        self.position_rmse_m = position_rmse_m
        self.timestamp_uncertainty_sec = timestamp_uncertainty_sec
        self._histories: dict[int, TrackHistory] = {}
        self._latest_records: dict[int, SpeedRecord] = {}
        self._kalman_filters: dict[int, KalmanFilter2D] = {}

    def update(
        self,
        tracker_id: int,
        pixel_center: tuple[float, float],
        timestamp_sec: float,
        process_noise: str | None = None,
    ) -> float | None:
        world_position = self.view_transformer.transform_point(*pixel_center)
        history = self._histories.setdefault(tracker_id, TrackHistory(tracker_id))
        previous_position = history.last_position
        previous_timestamp = history.last_timestamp
        history.add_position(world_position, timestamp_sec)

        if previous_position is None or previous_timestamp is None:
            if process_noise is not None:
                self._kalman_filters.setdefault(
                    tracker_id,
                    KalmanFilter2D(kalman_config_for_motion_profile(process_noise)),
                ).update(world_position, timestamp_sec)
            return None

        delta_t = timestamp_sec - previous_timestamp
        if delta_t <= 0:
            return None

        displacement = math.dist(previous_position, world_position)
        measured_velocity = (
            (world_position[0] - previous_position[0]) / delta_t,
            (world_position[1] - previous_position[1]) / delta_t,
        )
        uncertainty = estimate_speed_uncertainty(
            displacement_m=displacement,
            delta_t_sec=delta_t,
            position_rmse_m=self.position_rmse_m,
            timestamp_uncertainty_sec=self.timestamp_uncertainty_sec,
        )
        filtered_displacement = min_displacement_filter(displacement, self.min_displacement_m)
        if filtered_displacement == 0.0:
            speed_kmh = 0.0
            velocity_mps = (0.0, 0.0)
        elif process_noise is not None:
            kalman_state = self._kalman_filters.setdefault(
                tracker_id,
                KalmanFilter2D(kalman_config_for_motion_profile(process_noise)),
            ).update(world_position, timestamp_sec)
            speed_kmh = kalman_state.speed_kmh
            velocity_mps = kalman_state.velocity_mps
            uncertainty = estimate_speed_uncertainty(
                displacement_m=max(displacement, filtered_displacement),
                delta_t_sec=delta_t,
                position_rmse_m=self.position_rmse_m,
                timestamp_uncertainty_sec=self.timestamp_uncertainty_sec,
            )
        else:
            speed_kmh = (filtered_displacement / delta_t) * 3.6
            velocity_mps = measured_velocity

        filtered_speed_kmh = max_speed_filter(speed_kmh, self.max_speed_kmh)
        if filtered_speed_kmh is None:
            return None

        previous_speed_kmh = history.speeds_kmh[-1] if history.speeds_kmh else None
        history.speeds_kmh.append(filtered_speed_kmh)
        smoothed_speed = median_smoothing(history.speeds_kmh, self.smoothing_window)
        acceleration_mps2 = (
            ((filtered_speed_kmh - previous_speed_kmh) / 3.6) / delta_t
            if previous_speed_kmh is not None
            else None
        )
        self._latest_records[tracker_id] = SpeedRecord(
            tracker_id=tracker_id,
            speed_kmh=smoothed_speed,
            timestamp_sec=timestamp_sec,
            world_x=world_position[0],
            world_y=world_position[1],
            speed_uncertainty_kmh=uncertainty.speed_uncertainty_kmh,
            speed_confidence=uncertainty.speed_confidence,
            position_rmse_m=uncertainty.position_rmse_m,
            velocity_x_mps=velocity_mps[0],
            velocity_y_mps=velocity_mps[1],
            heading_deg=self._heading_deg(velocity_mps),
            acceleration_mps2=acceleration_mps2,
        )
        return smoothed_speed

    def get_record(self, tracker_id: int) -> SpeedRecord | None:
        return self._latest_records.get(tracker_id)

    def get_all_records(self) -> dict[int, SpeedRecord]:
        return dict(self._latest_records)

    def get_speed(self, tracker_id: int) -> float | None:
        record = self._latest_records.get(tracker_id)
        return record.speed_kmh if record is not None else None

    def get_all_speeds(self) -> dict[int, float]:
        return {tracker_id: record.speed_kmh for tracker_id, record in self._latest_records.items()}

    def reset(self) -> None:
        self._histories.clear()
        self._latest_records.clear()
        self._kalman_filters.clear()

    @staticmethod
    def _heading_deg(velocity_mps: tuple[float, float]) -> float | None:
        vx, vy = velocity_mps
        if abs(vx) < 1e-9 and abs(vy) < 1e-9:
            return None
        return float((math.degrees(math.atan2(vy, vx)) + 360.0) % 360.0)
