from __future__ import annotations

from domain.tracking.models import Track
from domain.zones.models import ZoneConfig, ZoneStats


class ZoneService:
    def __init__(self, zones: list[ZoneConfig], minimum_crossing_threshold: float = 0.0) -> None:
        self.zones = zones
        self.minimum_crossing_threshold = minimum_crossing_threshold
        self._stats = {zone.name: ZoneStats(zone.name) for zone in zones}
        self._last_points: dict[tuple[str, int], tuple[float, float]] = {}
        self._last_counted_direction: dict[tuple[str, int], str] = {}

    def trigger(self, tracks: list[Track]) -> list[ZoneStats]:
        for zone in self.zones:
            for track in tracks:
                key = (zone.name, track.tracker_id)
                current = track.bottom_center
                previous = self._last_points.get(key)
                if previous is not None:
                    direction = self._crossing_direction(zone, previous, current)
                    if direction is not None:
                        self._count_crossing(zone.name, key, direction)
                self._last_points[key] = current
        return self.get_stats()

    def get_stats(self) -> list[ZoneStats]:
        return [self._stats[zone.name] for zone in self.zones]

    def reset(self) -> None:
        self._stats = {zone.name: ZoneStats(zone.name) for zone in self.zones}
        self._last_points.clear()
        self._last_counted_direction.clear()

    def _count_crossing(
        self,
        zone_name: str,
        key: tuple[str, int],
        direction: str,
    ) -> None:
        if self._last_counted_direction.get(key) == direction:
            return
        stats = self._stats[zone_name]
        if direction == "in":
            self._stats[zone_name] = ZoneStats(stats.name, stats.in_count + 1, stats.out_count)
        elif direction == "out":
            self._stats[zone_name] = ZoneStats(stats.name, stats.in_count, stats.out_count + 1)
        self._last_counted_direction[key] = direction

    def _crossing_direction(
        self,
        zone: ZoneConfig,
        previous_point: tuple[float, float],
        current_point: tuple[float, float],
    ) -> str | None:
        previous_side = self._signed_side(zone, previous_point)
        current_side = self._signed_side(zone, current_point)
        if abs(previous_side) <= self.minimum_crossing_threshold:
            return None
        if abs(current_side) <= self.minimum_crossing_threshold:
            return None
        if previous_side * current_side >= 0.0:
            return None
        if not self._trajectory_intersects_counting_segment(zone, previous_point, current_point):
            return None
        return "in" if previous_side < current_side else "out"

    @staticmethod
    def _trajectory_intersects_counting_segment(
        zone: ZoneConfig,
        previous_point: tuple[float, float],
        current_point: tuple[float, float],
    ) -> bool:
        px, py = previous_point
        rx = current_point[0] - px
        ry = current_point[1] - py
        qx, qy = float(zone.line_start[0]), float(zone.line_start[1])
        sx = float(zone.line_end[0]) - qx
        sy = float(zone.line_end[1]) - qy
        denominator = rx * sy - ry * sx
        if abs(denominator) <= 1e-9:
            return False
        q_minus_p_x = qx - px
        q_minus_p_y = qy - py
        trajectory_t = (q_minus_p_x * sy - q_minus_p_y * sx) / denominator
        counting_line_t = (q_minus_p_x * ry - q_minus_p_y * rx) / denominator
        return 0.0 <= trajectory_t <= 1.0 and 0.0 <= counting_line_t <= 1.0

    @staticmethod
    def _signed_side(zone: ZoneConfig, point: tuple[float, float]) -> float:
        start_x, start_y = zone.line_start
        end_x, end_y = zone.line_end
        point_x, point_y = point
        line_dx = end_x - start_x
        line_dy = end_y - start_y
        line_length = (line_dx**2 + line_dy**2) ** 0.5
        return (line_dx * (point_y - start_y) - line_dy * (point_x - start_x)) / line_length
