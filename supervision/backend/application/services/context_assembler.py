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
        calibration_trusted = self._is_calibration_trusted(frame_report)
        motion_routes = self._build_motion_routes(frame_report, calibration_trusted)
        physical_state = self._build_physical_state(frame_report, calibration_trusted)
        risk_signals = self._build_risk_signals(
            frame_report=frame_report,
            scene_tags=scene_tags,
            location_label=location_label,
            calibration_trusted=calibration_trusted,
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
                "cite_speed_only_when_physics_valid_and_calibration_trusted",
                "separate_observation_from_inference",
                "prefer_low_cost_local_sensing",
            ],
        )

    def _build_motion_routes(
        self,
        frame_report: dict[str, Any],
        calibration_trusted: bool,
    ) -> list[dict[str, Any]]:
        routes: list[dict[str, Any]] = []
        for track in frame_report.get("active_tracks", []):
            profile = self.motion_router.route_class(int(track.get("class_id", -1)))
            measurement_trusted = calibration_trusted and track.get("physics_valid", False)
            routes.append(
                {
                    "tracker_id": track.get("tracker_id"),
                    "class_id": track.get("class_id"),
                    "class_name": track.get("class_name"),
                    "speed_kmh": track.get("speed_kmh") if measurement_trusted else None,
                    "speed_uncertainty_kmh": (
                        track.get("speed_uncertainty_kmh") if measurement_trusted else None
                    ),
                    "speed_confidence": (
                        track.get("speed_confidence") if measurement_trusted else None
                    ),
                    "speed_confidence_interval_kmh": (
                        track.get("speed_confidence_interval_kmh")
                        if measurement_trusted
                        else None
                    ),
                    "physics_valid": measurement_trusted,
                    "raw_physics_valid": track.get("physics_valid", False),
                    "calibration_trusted": calibration_trusted,
                    "quality_label": track.get("quality_label"),
                    "rejection_reason": track.get("rejection_reason"),
                    "track_age_frames": track.get("track_age_frames"),
                    "window_residual_m": track.get("window_residual_m"),
                    "ground_position_m": {
                        "x": track.get("ground_x_m") if measurement_trusted else None,
                        "y": track.get("ground_y_m") if measurement_trusted else None,
                    },
                    "velocity_mps": {
                        "x": track.get("velocity_x_mps") if measurement_trusted else None,
                        "y": track.get("velocity_y_mps") if measurement_trusted else None,
                    },
                    "heading_deg": track.get("heading_deg") if measurement_trusted else None,
                    "acceleration_mps2": (
                        track.get("acceleration_mps2") if measurement_trusted else None
                    ),
                    **profile.to_dict(),
                }
            )
        return routes

    @staticmethod
    def _build_physical_state(
        frame_report: dict[str, Any],
        calibration_trusted: bool,
    ) -> dict[str, Any]:
        active_tracks = frame_report.get("active_tracks", [])
        zone_stats = frame_report.get("zone_stats", [])
        speeds = [
            float(track["speed_kmh"])
            for track in active_tracks
            if calibration_trusted
            and track.get("speed_kmh") is not None
            and track.get("physics_valid", False)
        ]
        traffic_flow = frame_report.get("traffic_flow")
        if isinstance(traffic_flow, dict) and not calibration_trusted:
            traffic_flow = dict(traffic_flow)
            traffic_flow["space_mean_speed_kmh"] = None
        return {
            "frame_index": frame_report.get("frame_index"),
            "timestamp_sec": frame_report.get("timestamp_sec"),
            "fps": frame_report.get("fps"),
            "active_tracks": len(active_tracks),
            "total_in": int(frame_report.get("total_in", 0)),
            "total_out": int(frame_report.get("total_out", 0)),
            "avg_speed_kmh": sum(speeds) / len(speeds) if speeds else None,
            "calibration_trusted": calibration_trusted,
            "calibration_quality": frame_report.get("calibration_quality"),
            "calibration_diagnostics": frame_report.get("calibration_diagnostics"),
            "homography_grid": frame_report.get("homography_grid"),
            "traffic_flow": traffic_flow,
            "regional_people_count": frame_report.get("regional_people_count")
            or {
                "people_count": 0,
                "estimation_method": "unknown",
            },
            "infrastructure_semantics": frame_report.get("infrastructure_semantics")
            or {
                "traffic_light_count": 0,
                "traffic_light_state": "unknown",
            },
            "safety_metrics": frame_report.get("safety_metrics")
            or {
                "risk_level": "nominal",
            },
            "zones": [zone.get("name", "unknown") for zone in zone_stats],
        }

    def _build_risk_signals(
        self,
        frame_report: dict[str, Any],
        scene_tags: list[str],
        location_label: str | None,
        calibration_trusted: bool,
    ) -> list[dict[str, Any]]:
        signals: list[dict[str, Any]] = []
        sensitive_area = "school_zone" in scene_tags or "学校" in (location_label or "")
        for track in frame_report.get("active_tracks", []):
            if not calibration_trusted:
                continue
            speed = track.get("speed_kmh")
            if speed is None:
                continue
            if not track.get("physics_valid", False):
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
        safety_metrics = frame_report.get("safety_metrics") or {}
        red_light_violation_ids = safety_metrics.get("red_light_violation_track_ids") or []
        if calibration_trusted and red_light_violation_ids:
            signals.append(
                {
                    "type": "red_light_violation",
                    "severity": "critical",
                    "tracker_ids": red_light_violation_ids,
                    "traffic_light_state": (
                        (frame_report.get("infrastructure_semantics") or {}).get(
                            "traffic_light_state"
                        )
                    ),
                }
            )
        speeding_ids = safety_metrics.get("speeding_track_ids") or []
        if calibration_trusted and speeding_ids:
            signals.append(
                {
                    "type": "backend_speeding_rule",
                    "severity": "high" if sensitive_area else "medium",
                    "tracker_ids": speeding_ids,
                    "speed_limit_kmh": safety_metrics.get("speed_limit_kmh"),
                }
            )
        risk_level = safety_metrics.get("risk_level")
        if calibration_trusted and risk_level in {"critical", "elevated"}:
            signals.append(
                {
                    "type": "short_headway_or_collision_risk",
                    "severity": "high" if risk_level == "critical" else "medium",
                    "risk_level": risk_level,
                    "min_time_headway_sec": safety_metrics.get("min_time_headway_sec"),
                    "min_time_to_collision_sec": safety_metrics.get(
                        "min_time_to_collision_sec"
                    ),
                }
            )
        regional_people = frame_report.get("regional_people_count") or {}
        crowding_level = regional_people.get("crowding_level")
        if regional_people.get("density_integral_triggered") and crowding_level in {
            "critical",
            "crowded",
        }:
            signals.append(
                {
                    "type": "critical_crowd_density"
                    if crowding_level == "critical"
                    else "crowd_density_warning",
                    "severity": "critical" if crowding_level == "critical" else "high",
                    "people_count": regional_people.get("people_count"),
                    "integrated_people_count": regional_people.get("integrated_people_count"),
                    "density_people_per_sqm": regional_people.get("density_people_per_sqm"),
                    "estimation_method": regional_people.get("estimation_method"),
                    "crowding_level": crowding_level,
                }
            )
        infrastructure = frame_report.get("infrastructure_semantics") or {}
        if infrastructure.get("traffic_light_count", 0) > 0:
            signals.append(
                {
                    "type": "traffic_infrastructure_detected",
                    "severity": "low",
                    "traffic_light_count": infrastructure.get("traffic_light_count"),
                    "traffic_light_state": infrastructure.get("traffic_light_state"),
                }
            )
        if not signals:
            signals.append({"type": "normal_flow", "severity": "low"})
        return signals

    @staticmethod
    def _is_calibration_trusted(frame_report: dict[str, Any]) -> bool:
        diagnostics = frame_report.get("calibration_diagnostics")
        if isinstance(diagnostics, dict) and "calibration_trusted" in diagnostics:
            return bool(diagnostics.get("calibration_trusted"))
        homography_grid = frame_report.get("homography_grid")
        if isinstance(homography_grid, dict):
            return bool(homography_grid.get("calibration_trusted"))
        return False
