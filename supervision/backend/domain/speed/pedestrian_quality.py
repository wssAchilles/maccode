from __future__ import annotations

from typing import Any

PERSON_CLASS_ID = 0
PEDESTRIAN_ID_SWITCH_DISPLAY_THRESHOLD = 0.7


def annotate_pedestrian_speed_reports(
    frame_reports: list[dict[str, Any]],
    *,
    id_switch_display_threshold: float = PEDESTRIAN_ID_SWITCH_DISPLAY_THRESHOLD,
) -> list[dict[str, Any]]:
    for report in frame_reports:
        for track in report.get("active_tracks", []):
            if not isinstance(track, dict) or not _is_pedestrian(track):
                continue
            if not _is_displayable(track):
                continue
            if _id_switch_risk(track) < id_switch_display_threshold:
                track["pedestrian_speed_display_state"] = str(
                    track.get("pedestrian_speed_display_state") or "measured",
                )
                continue
            track["physics_valid"] = False
            track["speed_display_hidden"] = True
            track["pedestrian_speed_display_state"] = "id_switch_hidden"
            track["pedestrian_speed_display_rejection_reason"] = "id_switch_risk"
            track.setdefault("integrity_rejection_reason", "id_switch_risk")
    return frame_reports


def _is_pedestrian(track: dict[str, Any]) -> bool:
    return int(track.get("class_id", -1)) == PERSON_CLASS_ID or str(
        track.get("class_name") or "",
    ).lower() == "person"


def _is_displayable(track: dict[str, Any]) -> bool:
    return (
        track.get("speed_kmh") is not None
        and bool(track.get("physics_valid", False))
        and not bool(track.get("speed_display_hidden", False))
    )


def _id_switch_risk(track: dict[str, Any]) -> float:
    value = _float_or_none(track.get("id_switch_risk"))
    return max(0.0, min(1.0, value or 0.0))


def _float_or_none(value: object) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int | float | str):
        try:
            return float(value)
        except ValueError:
            return None
    return None
