from __future__ import annotations

import math

from shared.configs.constants import DEFAULT_MAX_SPEED_KMH, DEFAULT_MIN_DISPLACEMENT_M

from domain.speed.filters import max_speed_filter, min_displacement_filter
from domain.speed.models import SpeedRecord, TrackHistory
from domain.speed.smoothing import median_smoothing
from domain.speed.view_transformer import ViewTransformer


class SpeedEstimator:
    def __init__(
        self,
        view_transformer: ViewTransformer,
        smoothing_window: int = 5,
        min_displacement_m: float = DEFAULT_MIN_DISPLACEMENT_M,
        max_speed_kmh: float = DEFAULT_MAX_SPEED_KMH,
    ) -> None:
        self.view_transformer = view_transformer
        self.smoothing_window = smoothing_window
        self.min_displacement_m = min_displacement_m
        self.max_speed_kmh = max_speed_kmh
        self._histories: dict[int, TrackHistory] = {}
        self._latest_records: dict[int, SpeedRecord] = {}

    def update(
        self,
        tracker_id: int,
        pixel_center: tuple[float, float],
        timestamp_sec: float,
    ) -> float | None:
        world_position = self.view_transformer.transform_point(*pixel_center)
        history = self._histories.setdefault(tracker_id, TrackHistory(tracker_id))
        previous_position = history.last_position
        previous_timestamp = history.last_timestamp
        history.add_position(world_position, timestamp_sec)

        if previous_position is None or previous_timestamp is None:
            return None

        delta_t = timestamp_sec - previous_timestamp
        if delta_t <= 0:
            return None

        displacement = math.dist(previous_position, world_position)
        filtered_displacement = min_displacement_filter(displacement, self.min_displacement_m)
        if filtered_displacement == 0.0:
            speed_kmh = 0.0
        else:
            speed_kmh = (filtered_displacement / delta_t) * 3.6

        filtered_speed_kmh = max_speed_filter(speed_kmh, self.max_speed_kmh)
        if filtered_speed_kmh is None:
            return None

        history.speeds_kmh.append(filtered_speed_kmh)
        smoothed_speed = median_smoothing(history.speeds_kmh, self.smoothing_window)
        self._latest_records[tracker_id] = SpeedRecord(
            tracker_id=tracker_id,
            speed_kmh=smoothed_speed,
            timestamp_sec=timestamp_sec,
            world_x=world_position[0],
            world_y=world_position[1],
        )
        return smoothed_speed

    def get_speed(self, tracker_id: int) -> float | None:
        record = self._latest_records.get(tracker_id)
        return record.speed_kmh if record is not None else None

    def get_all_speeds(self) -> dict[int, float]:
        return {tracker_id: record.speed_kmh for tracker_id, record in self._latest_records.items()}

    def reset(self) -> None:
        self._histories.clear()
        self._latest_records.clear()
