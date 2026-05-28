from __future__ import annotations

from domain.tracking.models import Track
from domain.zones.models import ZoneConfig, ZoneStats


class ZoneService:
    def __init__(self, zones: list[ZoneConfig], minimum_crossing_threshold: float = 0.0) -> None:
        self.zones = zones
        self.minimum_crossing_threshold = minimum_crossing_threshold
        self._stats = {zone.name: ZoneStats(zone.name) for zone in zones}
        self._last_sides: dict[tuple[str, int], float] = {}

    def trigger(self, tracks: list[Track]) -> list[ZoneStats]:
        for zone in self.zones:
            for track in tracks:
                side = self._signed_side(zone, track.bottom_center)
                key = (zone.name, track.tracker_id)
                previous = self._last_sides.get(key)
                if previous is not None:
                    self._count_crossing(zone.name, previous, side)
                self._last_sides[key] = side
        return self.get_stats()

    def get_stats(self) -> list[ZoneStats]:
        return [self._stats[zone.name] for zone in self.zones]

    def reset(self) -> None:
        self._stats = {zone.name: ZoneStats(zone.name) for zone in self.zones}
        self._last_sides.clear()

    def _count_crossing(self, zone_name: str, previous: float, current: float) -> None:
        if abs(previous) <= self.minimum_crossing_threshold:
            return
        if abs(current) <= self.minimum_crossing_threshold:
            return
        stats = self._stats[zone_name]
        if previous < 0 < current:
            self._stats[zone_name] = ZoneStats(stats.name, stats.in_count + 1, stats.out_count)
        elif previous > 0 > current:
            self._stats[zone_name] = ZoneStats(stats.name, stats.in_count, stats.out_count + 1)

    @staticmethod
    def _signed_side(zone: ZoneConfig, point: tuple[float, float]) -> float:
        start_x, start_y = zone.line_start
        end_x, end_y = zone.line_end
        point_x, point_y = point
        return (end_x - start_x) * (point_y - start_y) - (end_y - start_y) * (point_x - start_x)
