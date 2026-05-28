from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from domain.motion.router import MotionRouter


@dataclass(frozen=True)
class DynamicContext:
    context_version: str
    scene: dict[str, Any]
    physical_state: dict[str, Any]
    motion_routes: list[dict[str, Any]]
    risk_signals: list[dict[str, Any]]
    decision_constraints: list[str]

    def to_prompt_payload(self) -> dict[str, Any]:
        return {
            "context_version": self.context_version,
            "scene": self.scene,
            "physical_state": self.physical_state,
            "motion_routes": self.motion_routes,
            "risk_signals": self.risk_signals,
            "decision_constraints": self.decision_constraints,
        }


class DynamicContextAssembler:
    def __init__(
        self, speed_limit_kmh: float = 80.0, motion_router: MotionRouter | None = None
    ) -> None:
        self.speed_limit_kmh = speed_limit_kmh
        self.motion_router = motion_router or MotionRouter()

    def assemble(
        self,
        frame_report: dict[str, Any],
        location_label: str | None = None,
        scene_tags: list[str] | None = None,
    ) -> DynamicContext:
        scene_tags = scene_tags or []
        motion_routes = self._build_motion_routes(frame_report)
        physical_state = self._build_physical_state(frame_report)
        risk_signals = self._build_risk_signals(
            frame_report=frame_report,
            scene_tags=scene_tags,
            location_label=location_label,
        )
        return DynamicContext(
            context_version="1.0",
            scene={
                "location_label": location_label or "未标注场景",
                "scene_tags": scene_tags,
            },
            physical_state=physical_state,
            motion_routes=motion_routes,
            risk_signals=risk_signals,
            decision_constraints=[
                "use_physical_json_only",
                "separate_observation_from_inference",
                "prefer_low_cost_local_sensing",
            ],
        )

    def _build_motion_routes(self, frame_report: dict[str, Any]) -> list[dict[str, Any]]:
        routes: list[dict[str, Any]] = []
        for track in frame_report.get("active_tracks", []):
            profile = self.motion_router.route_class(int(track.get("class_id", -1)))
            routes.append(
                {
                    "tracker_id": track.get("tracker_id"),
                    "class_id": track.get("class_id"),
                    "class_name": track.get("class_name"),
                    "speed_kmh": track.get("speed_kmh"),
                    "speed_uncertainty_kmh": track.get("speed_uncertainty_kmh"),
                    "speed_confidence": track.get("speed_confidence"),
                    **profile.to_dict(),
                }
            )
        return routes

    @staticmethod
    def _build_physical_state(frame_report: dict[str, Any]) -> dict[str, Any]:
        active_tracks = frame_report.get("active_tracks", [])
        zone_stats = frame_report.get("zone_stats", [])
        speeds = [
            float(track["speed_kmh"])
            for track in active_tracks
            if track.get("speed_kmh") is not None
        ]
        return {
            "frame_index": frame_report.get("frame_index"),
            "timestamp_sec": frame_report.get("timestamp_sec"),
            "fps": frame_report.get("fps"),
            "active_tracks": len(active_tracks),
            "total_in": int(frame_report.get("total_in", 0)),
            "total_out": int(frame_report.get("total_out", 0)),
            "avg_speed_kmh": sum(speeds) / len(speeds) if speeds else None,
            "calibration_quality": frame_report.get("calibration_quality"),
            "traffic_flow": frame_report.get("traffic_flow"),
            "zones": [zone.get("name", "unknown") for zone in zone_stats],
        }

    def _build_risk_signals(
        self,
        frame_report: dict[str, Any],
        scene_tags: list[str],
        location_label: str | None,
    ) -> list[dict[str, Any]]:
        signals: list[dict[str, Any]] = []
        sensitive_area = "school_zone" in scene_tags or "学校" in (location_label or "")
        for track in frame_report.get("active_tracks", []):
            speed = track.get("speed_kmh")
            if speed is None:
                continue
            if float(speed) > self.speed_limit_kmh and sensitive_area:
                signals.append(
                    {
                        "type": "speeding_near_sensitive_area",
                        "severity": "high",
                        "tracker_id": track.get("tracker_id"),
                        "speed_kmh": float(speed),
                        "threshold_kmh": self.speed_limit_kmh,
                    }
                )
            elif float(speed) > self.speed_limit_kmh:
                signals.append(
                    {
                        "type": "speeding",
                        "severity": "medium",
                        "tracker_id": track.get("tracker_id"),
                        "speed_kmh": float(speed),
                        "threshold_kmh": self.speed_limit_kmh,
                    }
                )
        if not signals:
            signals.append({"type": "normal_flow", "severity": "low"})
        return signals
