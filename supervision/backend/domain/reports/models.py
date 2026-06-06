from __future__ import annotations

from dataclasses import asdict, dataclass

from domain.tracking.models import Track
from domain.zones.models import ZoneStats


@dataclass(frozen=True)
class FrameReport:
    frame_index: int
    timestamp_sec: float
    fps: float
    active_tracks: list[Track]
    zone_stats: list[ZoneStats]
    total_in: int
    total_out: int
    calibration_quality: str | None = None
    calibration_diagnostics: dict[str, object] | None = None
    homography_grid: dict[str, object] | None = None
    traffic_flow: dict[str, object] | None = None
    regional_people_count: dict[str, object] | None = None
    infrastructure_semantics: dict[str, object] | None = None
    safety_metrics: dict[str, object] | None = None
    bev_confidence_map: dict[str, object] | None = None
    integrity_diagnostics: dict[str, object] | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "frame_index": self.frame_index,
            "timestamp_sec": self.timestamp_sec,
            "fps": self.fps,
            "active_tracks": [asdict(track) for track in self.active_tracks],
            "zone_stats": [asdict(stat) for stat in self.zone_stats],
            "total_in": self.total_in,
            "total_out": self.total_out,
            "calibration_quality": self.calibration_quality,
            "calibration_diagnostics": self.calibration_diagnostics,
            "homography_grid": self.homography_grid,
            "traffic_flow": self.traffic_flow,
            "regional_people_count": self.regional_people_count,
            "infrastructure_semantics": self.infrastructure_semantics,
            "safety_metrics": self.safety_metrics,
            "bev_confidence_map": self.bev_confidence_map,
            "integrity_diagnostics": self.integrity_diagnostics,
        }


@dataclass(frozen=True)
class CumulativeStats:
    total_frames: int
    total_unique_tracks: int
    zone_stats: list[ZoneStats]
    avg_fps: float
    avg_speed_kmh: float | None
    processing_time_sec: float
    avg_speed_confidence: float | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "total_frames": self.total_frames,
            "total_unique_tracks": self.total_unique_tracks,
            "zone_stats": [asdict(stat) for stat in self.zone_stats],
            "avg_fps": self.avg_fps,
            "avg_speed_kmh": self.avg_speed_kmh,
            "processing_time_sec": self.processing_time_sec,
            "avg_speed_confidence": self.avg_speed_confidence,
        }
