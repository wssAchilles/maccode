from __future__ import annotations

from statistics import mean

from shared.configs.constants import DEFAULT_REPORT_INTERVAL

from domain.reports.models import CumulativeStats, FrameReport
from domain.speed.models import SpeedRecord
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
        speed_records: dict[int, SpeedRecord] | None = None,
        calibration_quality: str | None = None,
        traffic_flow: dict[str, object] | None = None,
        regional_people_count: dict[str, object] | None = None,
        infrastructure_semantics: dict[str, object] | None = None,
        safety_metrics: dict[str, object] | None = None,
    ) -> FrameReport:
        speeds = speeds or {}
        speed_records = speed_records or {}
        tracks_with_speed = [
            self._apply_speed(track, speeds, speed_records) for track in tracks
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
            calibration_quality=calibration_quality,
            traffic_flow=traffic_flow,
            regional_people_count=regional_people_count,
            infrastructure_semantics=infrastructure_semantics,
            safety_metrics=safety_metrics,
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
        confidences = [
            track.speed_confidence
            for frame in self._frames
            for track in frame.active_tracks
            if track.speed_confidence is not None
        ]
        last_frame = self._frames[-1]
        return CumulativeStats(
            total_frames=len(self._frames),
            total_unique_tracks=len(self._seen_track_ids),
            zone_stats=last_frame.zone_stats,
            avg_fps=mean(frame.fps for frame in self._frames),
            avg_speed_kmh=mean(speeds) if speeds else None,
            processing_time_sec=last_frame.timestamp_sec - self._frames[0].timestamp_sec,
            avg_speed_confidence=mean(confidences) if confidences else None,
        )

    def reset(self) -> None:
        self._frames.clear()
        self._seen_track_ids.clear()

    @staticmethod
    def _apply_speed(
        track: Track,
        speeds: dict[int, float | None],
        speed_records: dict[int, SpeedRecord],
    ) -> Track:
        record = speed_records.get(track.tracker_id)
        if record is not None:
            return track.with_speed(
                record.speed_kmh,
                speed_uncertainty_kmh=record.speed_uncertainty_kmh,
                speed_confidence=record.speed_confidence,
                speed_confidence_interval_kmh=ReportGenerator._confidence_interval(record),
                position_rmse_m=record.position_rmse_m,
                ground_x_m=record.world_x,
                ground_y_m=record.world_y,
                velocity_x_mps=record.velocity_x_mps,
                velocity_y_mps=record.velocity_y_mps,
                heading_deg=record.heading_deg,
                acceleration_mps2=record.acceleration_mps2,
            )
        return track.with_speed(speeds.get(track.tracker_id, track.speed_kmh))

    @staticmethod
    def _confidence_interval(record: SpeedRecord) -> list[float] | None:
        if record.speed_uncertainty_kmh is None:
            return None
        lower = max(0.0, record.speed_kmh - record.speed_uncertainty_kmh)
        upper = record.speed_kmh + record.speed_uncertainty_kmh
        return [float(lower), float(upper)]
