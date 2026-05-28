from __future__ import annotations

from dataclasses import asdict, dataclass
from statistics import mean
from typing import Any
from uuid import uuid4

from domain.zones.models import ZoneConfig, ZoneStats
from scripts.generate_demo_report import generate_demo_report


@dataclass(frozen=True)
class ProcessingTask:
    task_id: str
    source: str
    status: str
    frame_count: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class DemoRuntime:
    def __init__(self) -> None:
        self._zones = [ZoneConfig("main_gate", [0, 10], [80, 10])]
        self._history: list[dict[str, Any]] = []
        self._tasks: dict[str, ProcessingTask] = {}

    def get_realtime_report(self) -> dict[str, Any]:
        if not self._history:
            self._history.append(self._with_current_zones(generate_demo_report()))
        return self._history[-1]

    def get_history(self, limit: int = 100) -> list[dict[str, Any]]:
        self.get_realtime_report()
        return self._history[-limit:]

    def get_cumulative_stats(self) -> dict[str, Any]:
        history = self.get_history()
        track_ids = {
            track["tracker_id"] for report in history for track in report.get("active_tracks", [])
        }
        speeds = [
            float(track["speed_kmh"])
            for report in history
            for track in report.get("active_tracks", [])
            if track.get("speed_kmh") is not None
        ]
        fps_values = [float(report["fps"]) for report in history]
        return {
            "total_frames": len(history),
            "total_unique_tracks": len(track_ids),
            "zone_stats": history[-1]["zone_stats"],
            "avg_fps": mean(fps_values) if fps_values else 0.0,
            "avg_speed_kmh": mean(speeds) if speeds else None,
            "processing_time_sec": float(history[-1]["timestamp_sec"])
            - float(history[0]["timestamp_sec"]),
        }

    def start_task(self, source: str) -> ProcessingTask:
        report = self._with_current_zones(generate_demo_report())
        self._history.append(report)
        task = ProcessingTask(
            task_id=str(uuid4()),
            source=source,
            status="running",
            frame_count=len(self._history),
        )
        self._tasks[task.task_id] = task
        return task

    def stop_task(self, task_id: str) -> ProcessingTask | None:
        task = self._tasks.get(task_id)
        if task is None:
            return None
        stopped = ProcessingTask(task.task_id, task.source, "stopped", task.frame_count)
        self._tasks[task_id] = stopped
        return stopped

    def get_task(self, task_id: str) -> ProcessingTask | None:
        return self._tasks.get(task_id)

    def get_zones(self) -> list[ZoneConfig]:
        return self._zones

    def update_zones(self, zones: list[ZoneConfig]) -> list[ZoneConfig]:
        if not zones:
            raise ValueError("at least one zone is required")
        self._zones = zones
        if self._history:
            self._history[-1] = self._with_current_zones(self._history[-1])
        return self._zones

    def _with_current_zones(self, report: dict[str, Any]) -> dict[str, Any]:
        zone_stats = report.get("zone_stats", [])
        first_stat = zone_stats[0] if zone_stats else {"in_count": 0, "out_count": 0}
        updated = dict(report)
        updated["zone_stats"] = [
            asdict(
                ZoneStats(
                    name=zone.name,
                    in_count=int(first_stat.get("in_count", 0)),
                    out_count=int(first_stat.get("out_count", 0)),
                )
            )
            for zone in self._zones
        ]
        updated["total_in"] = sum(zone["in_count"] for zone in updated["zone_stats"])
        updated["total_out"] = sum(zone["out_count"] for zone in updated["zone_stats"])
        return updated
