from __future__ import annotations

from statistics import mean

from shared.configs.constants import DEFAULT_REPORT_INTERVAL

from domain.reports.models import CumulativeStats, FrameReport
from domain.tracking.models import Track
from domain.zones.models import ZoneStats


class ReportGenerator:
    def __init__(self, report_interval: int = DEFAULT_REPORT_INTERVAL) -> None:
        self.report_interval = report_interval
        self._frames: list[FrameReport] = []
        self._seen_track_ids: set[int] = set()

    def should_report(self, frame_index: int) -> bool:
        return frame_index % self.report_interval == 0

    def add_frame(
        self,
        frame_index: int,
        timestamp_sec: float,
        tracks: list[Track],
        zone_stats: list[ZoneStats],
        fps: float,
        speeds: dict[int, float | None] | None = None,
    ) -> FrameReport:
        speeds = speeds or {}
        tracks_with_speed = [
            track.with_speed(speeds.get(track.tracker_id, track.speed_kmh)) for track in tracks
        ]
        self._seen_track_ids.update(track.tracker_id for track in tracks_with_speed)
        report = FrameReport(
            frame_index=frame_index,
            timestamp_sec=timestamp_sec,
            fps=fps,
            active_tracks=tracks_with_speed,
            zone_stats=zone_stats,
            total_in=sum(stats.in_count for stats in zone_stats),
            total_out=sum(stats.out_count for stats in zone_stats),
        )
        self._frames.append(report)
        return report

    def generate_cumulative_stats(self) -> CumulativeStats:
        if not self._frames:
            return CumulativeStats(0, 0, [], 0.0, None, 0.0)

        speeds = [
            track.speed_kmh
            for frame in self._frames
            for track in frame.active_tracks
            if track.speed_kmh is not None
        ]
        last_frame = self._frames[-1]
        return CumulativeStats(
            total_frames=len(self._frames),
            total_unique_tracks=len(self._seen_track_ids),
            zone_stats=last_frame.zone_stats,
            avg_fps=mean(frame.fps for frame in self._frames),
            avg_speed_kmh=mean(speeds) if speeds else None,
            processing_time_sec=last_frame.timestamp_sec - self._frames[0].timestamp_sec,
        )

    def reset(self) -> None:
        self._frames.clear()
        self._seen_track_ids.clear()
