from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean
from typing import Any
from uuid import uuid4

import yaml
from domain.zones.models import ZoneConfig, ZoneStats
from scripts.generate_demo_report import generate_demo_report

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CALIBRATION_PRESET_YAML = PROJECT_ROOT / "data/tests/calibration_presets.yaml"
CALIBRATION_PRESET_JSON = PROJECT_ROOT / "data/tests/calibration_presets.json"
GOLDEN_TUNING_YAML = PROJECT_ROOT / "data/tests/golden_tuning.yaml"
CAMERA_PROFILES_YAML = PROJECT_ROOT / "data/tests/camera_profiles.yaml"
PROCESSED_VIDEO_DIR = PROJECT_ROOT / "data/outputs/processed_videos"
LOCAL_API_BASE_URL = "http://127.0.0.1:8000"


@dataclass(frozen=True)
class ProcessingTask:
    task_id: str
    source: str
    status: str
    frame_count: int
    analysis_status: str = "demo"
    analysis_source: str = "synthetic"
    analysis_device: str | None = None
    analysis_error: str | None = None
    analysis_clip: str | None = None
    calibration_source: str | None = None
    processed_video_path: str | None = None
    processed_video_url: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class DemoRuntime:
    def __init__(self) -> None:
        self._zones = [ZoneConfig("main_gate", [0, 10], [80, 10])]
        self._history: list[dict[str, Any]] = []
        self._tasks: dict[str, ProcessingTask] = {}
        self._playback_index = 0

    def get_realtime_report(self) -> dict[str, Any]:
        if not self._history:
            self._history.append(self._with_current_zones(generate_demo_report()))
        if len(self._history) <= 1:
            return self._history[-1]
        report = self._history[self._playback_index % len(self._history)]
        self._playback_index = (self._playback_index + 1) % len(self._history)
        return report

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
        report, analysis_meta, frame_reports = self._report_for_source(source)
        if frame_reports:
            self._history = frame_reports
            self._playback_index = 0
        else:
            self._history.append(report)
            self._playback_index = max(0, len(self._history) - 1)
        task = ProcessingTask(
            task_id=str(uuid4()),
            source=source,
            status="running",
            frame_count=len(self._history),
            analysis_status=str(analysis_meta["analysis_status"]),
            analysis_source=str(analysis_meta["analysis_source"]),
            analysis_device=analysis_meta.get("analysis_device"),
            analysis_error=analysis_meta.get("analysis_error"),
            analysis_clip=analysis_meta.get("analysis_clip"),
            calibration_source=analysis_meta.get("calibration_source"),
            processed_video_path=analysis_meta.get("processed_video_path"),
            processed_video_url=analysis_meta.get("processed_video_url"),
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

    def _report_for_source(
        self,
        source: str,
    ) -> tuple[dict[str, Any], dict[str, str | None], list[dict[str, Any]]]:
        video_suffixes = (".avi", ".mkv", ".mov", ".mp4", ".webm")
        if source.startswith("file://") or source.endswith(video_suffixes):
            path = Path(source.removeprefix("file://"))
            try:
                analysis = self._analyze_video_source(path)
                report = self._with_current_zones(analysis["final_report"])
                frame_reports = [
                    self._with_current_zones(frame_report)
                    for frame_report in analysis.get("frame_reports", [])
                ]
                return report, {
                    "analysis_status": "real_video",
                    "analysis_source": "yolo_supervision_math",
                    "analysis_device": (
                        str(analysis.get("device")) if analysis.get("device") else None
                    ),
                    "analysis_clip": analysis["clip"],
                    "calibration_source": analysis["calibration"]["source"],
                    "processed_video_path": analysis["processed_video"]["path"],
                    "processed_video_url": self._processed_video_url(
                        analysis["processed_video"]["path"],
                    ),
                }, frame_reports
            except Exception as exc:  # noqa: BLE001
                report = self._with_current_zones(generate_demo_report())
                return report, {
                    "analysis_status": "fallback_demo",
                    "analysis_source": "synthetic",
                    "analysis_error": str(exc),
                }, []

        return self._with_current_zones(generate_demo_report()), {
            "analysis_status": "demo",
            "analysis_source": "synthetic",
        }, []

    def _analyze_video_source(self, path: Path) -> dict[str, Any]:
        from scripts.analyze_real_videos import (  # noqa: PLC0415
            CalibrationPresetCatalog,
            analyze_clip,
            load_calibration_presets,
            load_camera_profiles,
            resolve_device,
        )
        from shared.configs.settings import Settings  # noqa: PLC0415

        settings = Settings()
        preset_path = (
            CALIBRATION_PRESET_YAML
            if CALIBRATION_PRESET_YAML.exists()
            else CALIBRATION_PRESET_JSON
        )
        presets = load_calibration_presets(preset_path)
        presets = CalibrationPresetCatalog(
            scene_profiles=presets.scene_profiles,
            video_calibrations=presets.video_calibrations,
            camera_profiles=load_camera_profiles(CAMERA_PROFILES_YAML),
        )
        tuning = self._tuning_for_clip(path.name)
        return analyze_clip(
            path=path,
            model_path=settings.cv.yolo_model,
            device=resolve_device(settings.cv.yolo_device),
            confidence=tuning.get(
                "confidence_threshold",
                max(settings.cv.confidence_threshold, 0.35),
            ),
            frame_stride=int(tuning.get("runtime_frame_stride", 1)),
            max_frames=None,
            presets=presets,
            processed_output_dir=PROCESSED_VIDEO_DIR,
        )

    @staticmethod
    def _tuning_for_clip(clip_name: str) -> dict[str, Any]:
        if not GOLDEN_TUNING_YAML.exists():
            return {}
        payload = yaml.safe_load(GOLDEN_TUNING_YAML.read_text()) or {}
        clips = payload.get("clips", {})
        entry = clips.get(clip_name) if isinstance(clips, dict) else None
        return entry if isinstance(entry, dict) else {}

    @staticmethod
    def _processed_video_url(path_value: object) -> str | None:
        if not path_value:
            return None
        path = Path(str(path_value))
        try:
            relative = path.relative_to(PROCESSED_VIDEO_DIR.parent)
        except ValueError:
            return None
        version = path.stat().st_mtime_ns if path.exists() else 0
        return f"{LOCAL_API_BASE_URL}/media/{relative.as_posix()}?v={version}"
