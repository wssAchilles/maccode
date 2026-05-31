from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from infrastructure.cognition.prompts.atomic_blocks import (
    error_model,
    spatial_context,
    temporal_context,
)
from infrastructure.cognition.prompts.base import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from infrastructure.llm.providers.base_provider import LLMMessage


@dataclass(frozen=True)
class PromptAssembler:
    def build_messages(
        self,
        frame_report: dict[str, Any],
        dynamic_context: dict[str, Any],
        location_label: str | None = None,
        scene_tags: list[str] | None = None,
    ) -> list[LLMMessage]:
        keys = self._context_keys(location_label=location_label, scene_tags=scene_tags)
        user_prompt = USER_PROMPT_TEMPLATE.format(
            spatial_context=spatial_context.get_prompt(keys),
            temporal_context=temporal_context.get_prompt(keys),
            error_model_context=error_model.get_prompt(keys),
            dynamic_context_json=json.dumps(
                self.sanitize_dynamic_context(dynamic_context),
                ensure_ascii=False,
                indent=2,
            ),
            frame_report_json=json.dumps(
                self.sanitize_frame_report(frame_report),
                ensure_ascii=False,
                indent=2,
            ),
        )
        return [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

    @staticmethod
    def sanitize_frame_report(frame_report: dict[str, Any]) -> dict[str, Any]:
        sanitized = dict(frame_report)
        calibration_trusted = PromptAssembler._is_calibration_trusted(frame_report)
        tracks = []
        for track in frame_report.get("active_tracks", []):
            if not isinstance(track, dict):
                continue
            next_track = dict(track)
            if not calibration_trusted or not next_track.get("physics_valid", False):
                PromptAssembler._clear_motion_measurements(next_track)
            tracks.append(next_track)
        sanitized["active_tracks"] = tracks
        if not calibration_trusted:
            traffic_flow = sanitized.get("traffic_flow")
            if isinstance(traffic_flow, dict):
                sanitized["traffic_flow"] = dict(traffic_flow) | {
                    "space_mean_speed_kmh": None
                }
            safety_metrics = sanitized.get("safety_metrics")
            if isinstance(safety_metrics, dict):
                sanitized["safety_metrics"] = dict(safety_metrics) | {
                    "speeding_track_ids": [],
                    "min_time_headway_sec": None,
                    "min_time_to_collision_sec": None,
                }
        return sanitized

    @staticmethod
    def sanitize_dynamic_context(dynamic_context: dict[str, Any]) -> dict[str, Any]:
        sanitized = dict(dynamic_context)
        physical_state = sanitized.get("physical_state")
        calibration_trusted = True
        if isinstance(physical_state, dict):
            calibration_trusted = bool(physical_state.get("calibration_trusted", False))
        routes = []
        for route in dynamic_context.get("motion_routes", []):
            if not isinstance(route, dict):
                continue
            next_route = dict(route)
            if not calibration_trusted or not next_route.get("physics_valid", False):
                PromptAssembler._clear_motion_measurements(next_route)
            routes.append(next_route)
        sanitized["motion_routes"] = routes
        return sanitized

    @staticmethod
    def _clear_motion_measurements(item: dict[str, Any]) -> None:
        item["speed_kmh"] = None
        item["speed_uncertainty_kmh"] = None
        item["speed_confidence"] = None
        item["speed_confidence_interval_kmh"] = None
        item["ground_x_m"] = None
        item["ground_y_m"] = None
        item["velocity_x_mps"] = None
        item["velocity_y_mps"] = None
        item["heading_deg"] = None
        item["acceleration_mps2"] = None
        if isinstance(item.get("ground_position_m"), dict):
            item["ground_position_m"] = {"x": None, "y": None}
        if isinstance(item.get("velocity_mps"), dict):
            item["velocity_mps"] = {"x": None, "y": None}

    @staticmethod
    def _is_calibration_trusted(frame_report: dict[str, Any]) -> bool:
        diagnostics = frame_report.get("calibration_diagnostics")
        if isinstance(diagnostics, dict) and "calibration_trusted" in diagnostics:
            return bool(diagnostics.get("calibration_trusted"))
        homography_grid = frame_report.get("homography_grid")
        if isinstance(homography_grid, dict):
            return bool(homography_grid.get("calibration_trusted"))
        return False

    @staticmethod
    def _context_keys(location_label: str | None, scene_tags: list[str] | None) -> list[str]:
        raw_keys = [*(scene_tags or [])]
        if location_label:
            raw_keys.append(location_label)
        aliases = {
            "学校": "school_zone",
            "学校门口": "school_zone",
            "school": "school_zone",
            "医院": "hospital_gate",
            "医院门口": "hospital_gate",
            "hospital": "hospital_gate",
            "路口": "intersection",
            "十字路口": "intersection",
            "intersection": "intersection",
            "斑马线": "crosswalk",
            "crosswalk": "crosswalk",
            "深夜": "night",
            "凌晨": "late_night",
            "night": "night",
            "雨": "rain",
            "雨天": "rain",
            "rain": "rain",
            "积水": "waterlogging",
            "waterlogging": "waterlogging",
            "高峰": "rush_hour",
            "早高峰": "rush_hour",
            "晚高峰": "rush_hour",
            "rush_hour": "rush_hour",
            "low_confidence": "low_confidence",
            "uncertainty": "uncertainty",
        }
        keys: list[str] = []
        for raw_key in raw_keys:
            normalized = raw_key.strip().lower().replace("-", "_").replace(" ", "_")
            for alias, key in aliases.items():
                if alias in normalized or alias in raw_key:
                    keys.append(key)
            keys.append(normalized)
        return list(dict.fromkeys(key for key in keys if key))
