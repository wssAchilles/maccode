from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from domain.detection.models import Detections
from domain.tracking.models import Track
from domain.zones.models import ZoneStats


@dataclass(frozen=True)
class SupervisionAdapterResult:
    tracks: list[Track]
    zone_stats: ZoneStats


class SupervisionRuntimeAdapter:
    _DEFAULT_TRACKER_CONFIG = {
        "track_activation_threshold": 0.25,
        "lost_track_buffer": 30,
        "minimum_matching_threshold": 0.8,
        "frame_rate": 30.0,
    }

    def __init__(
        self,
        track_activation_threshold: float | None = None,
        lost_track_buffer: int | None = None,
        minimum_matching_threshold: float | None = None,
        frame_rate: float | None = None,
    ) -> None:
        self._tracker: Any | None = None
        self._line_zones: dict[tuple[str, float, float, float, float], Any] = {}
        explicit_config = {
            "track_activation_threshold": track_activation_threshold,
            "lost_track_buffer": lost_track_buffer,
            "minimum_matching_threshold": minimum_matching_threshold,
            "frame_rate": frame_rate,
        }
        self._tracker_kwargs = {
            key: value for key, value in explicit_config.items() if value is not None
        }
        self._tracker_config = dict(self._DEFAULT_TRACKER_CONFIG)
        self._tracker_config.update(self._tracker_kwargs)
        self._tracker_config_fallback_used = False
        self._unsupported_tracker_kwargs: list[str] = []

    def track_and_count(
        self,
        detections: Detections,
        line_start: tuple[float, float],
        line_end: tuple[float, float],
        zone_name: str = "main_gate",
    ) -> SupervisionAdapterResult:
        try:
            import supervision as sv  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError("supervision is required for the real CV runtime adapter") from exc

        xyxy = np.array([item.xyxy for item in detections.items], dtype=float)
        if xyxy.size == 0:
            xyxy = np.empty((0, 4), dtype=float)
        sv_detections = sv.Detections(
            xyxy=xyxy,
            confidence=np.array([item.confidence for item in detections.items], dtype=float),
            class_id=np.array([item.class_id for item in detections.items], dtype=int),
        )
        tracker = self._get_tracker(sv)
        tracked = tracker.update_with_detections(sv_detections)
        line_zone = self._get_line_zone(sv, line_start, line_end, zone_name)
        line_zone.trigger(tracked)

        return SupervisionAdapterResult(
            tracks=self._to_domain_tracks(tracked, detections),
            zone_stats=ZoneStats(zone_name, int(line_zone.in_count), int(line_zone.out_count)),
        )

    def _get_tracker(self, sv: Any) -> Any:
        if self._tracker is None:
            if self._tracker_kwargs:
                try:
                    self._tracker = sv.ByteTrack(**self._tracker_kwargs)
                except TypeError:
                    self._tracker_config_fallback_used = True
                    self._unsupported_tracker_kwargs = list(self._tracker_kwargs)
                    self._tracker = sv.ByteTrack()
            else:
                self._tracker = sv.ByteTrack()
        return self._tracker

    def diagnostics_dict(self) -> dict[str, object]:
        return {
            "tracker_type": "ByteTrack",
            "tracker_config": dict(self._tracker_config),
            "tracker_config_fallback_used": self._tracker_config_fallback_used,
            "unsupported_tracker_kwargs": list(self._unsupported_tracker_kwargs),
            "line_zone_count": len(self._line_zones),
        }

    def _get_line_zone(
        self,
        sv: Any,
        line_start: tuple[float, float],
        line_end: tuple[float, float],
        zone_name: str,
    ) -> Any:
        key = (
            zone_name,
            float(line_start[0]),
            float(line_start[1]),
            float(line_end[0]),
            float(line_end[1]),
        )
        if key not in self._line_zones:
            self._line_zones[key] = sv.LineZone(
                start=sv.Point(x=line_start[0], y=line_start[1]),
                end=sv.Point(x=line_end[0], y=line_end[1]),
            )
        return self._line_zones[key]

    @staticmethod
    def _to_domain_tracks(tracked: Any, source: Detections) -> list[Track]:
        tracker_ids = getattr(tracked, "tracker_id", [])
        class_names_by_id = {
            detection.class_id: detection.class_name for detection in source.items
        }
        tracks: list[Track] = []
        for index, tracker_id in enumerate(tracker_ids):
            class_id = int(tracked.class_id[index])
            tracks.append(
                Track(
                    tracker_id=int(tracker_id),
                    class_id=class_id,
                    class_name=class_names_by_id.get(class_id, str(class_id)),
                    confidence=float(tracked.confidence[index]),
                    xyxy=[float(value) for value in tracked.xyxy[index]],
                    first_seen_frame=source.frame_index,
                    last_seen_frame=source.frame_index,
                )
            )
        return tracks
