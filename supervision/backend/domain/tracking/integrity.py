from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

from domain.speed.models import SpeedRecord
from domain.tracking.models import Track

TrackingIntegrityState = Literal[
    "normal",
    "suspected_id_switch",
    "occluded",
    "recovered",
    "unstable_association",
]


@dataclass(frozen=True)
class TrackingIntegrityResult:
    state: TrackingIntegrityState
    id_switch_risk: float
    speed_frozen: bool
    rejection_reason: str | None
    reset_speed_history: bool = False


@dataclass
class _IntegrityState:
    previous_world: tuple[float, float] | None = None
    previous_timestamp_sec: float | None = None
    previous_bbox: list[float] | None = None
    previous_class_id: int | None = None
    freeze_remaining: int = 0
    anomaly_streak: int = 0
    missed_frames: int = 0


class TrackingIntegrityMonitor:
    """Detect association anomalies after tracker output, before speed state update."""

    def __init__(self, freeze_frames: int = 3) -> None:
        self.freeze_frames = freeze_frames
        self._states: dict[int, _IntegrityState] = {}

    def assess(
        self,
        track: Track,
        *,
        world_position: tuple[float, float],
        timestamp_sec: float,
        previous_record: SpeedRecord | None,
        active_track_ids: set[int],
    ) -> TrackingIntegrityResult:
        state = self._states.setdefault(track.tracker_id, _IntegrityState())
        reason: str | None = None
        risk = 0.0

        if state.previous_class_id is not None and state.previous_class_id != track.class_id:
            risk = max(risk, 0.9)
            reason = "class_changed"

        if state.previous_bbox is not None:
            bbox_risk, bbox_reason = self._bbox_jump_risk(state.previous_bbox, track.xyxy)
            if bbox_risk > risk:
                risk = bbox_risk
                reason = bbox_reason

        if (
            previous_record is not None
            and previous_record.physics_valid
            and previous_record.velocity_x_mps is not None
            and previous_record.velocity_y_mps is not None
        ):
            delta_t = timestamp_sec - previous_record.timestamp_sec
            if delta_t > 0:
                predicted = (
                    previous_record.world_x + previous_record.velocity_x_mps * delta_t,
                    previous_record.world_y + previous_record.velocity_y_mps * delta_t,
                )
                error_m = math.dist(predicted, world_position)
                gate_m = max(4.0, (previous_record.speed_kmh or 0.0) / 3.6 * delta_t * 3.0)
                if error_m > gate_m:
                    risk = max(risk, min(1.0, error_m / max(gate_m * 2.0, 1e-6)))
                    reason = "bev_prediction_jump"

        if state.previous_world is not None and state.previous_timestamp_sec is not None:
            delta_t = timestamp_sec - state.previous_timestamp_sec
            if delta_t > 0:
                implied_speed_kmh = math.dist(state.previous_world, world_position) / delta_t * 3.6
                if implied_speed_kmh > 180.0:
                    risk = max(risk, min(1.0, implied_speed_kmh / 240.0))
                    reason = "world_position_jump"

        if risk >= 0.75:
            state.anomaly_streak += 1
            state.freeze_remaining = max(state.freeze_remaining, self.freeze_frames)
            result_state: TrackingIntegrityState = "suspected_id_switch"
        elif state.freeze_remaining > 0:
            state.freeze_remaining -= 1
            state.anomaly_streak = 0
            result_state = "recovered" if state.freeze_remaining == 0 else "unstable_association"
            risk = max(risk, 0.35)
            reason = reason or "recovering_from_association_anomaly"
        else:
            state.anomaly_streak = 0
            result_state = "normal"

        reset = state.anomaly_streak >= self.freeze_frames
        speed_frozen = state.freeze_remaining > 0 or result_state == "suspected_id_switch"
        self._remember(state, track, world_position, timestamp_sec)
        self._drop_missing(active_track_ids)
        return TrackingIntegrityResult(
            state=result_state,
            id_switch_risk=float(max(0.0, min(1.0, risk))),
            speed_frozen=speed_frozen,
            rejection_reason=reason,
            reset_speed_history=reset,
        )

    def _drop_missing(self, active_track_ids: set[int]) -> None:
        for tracker_id, state in list(self._states.items()):
            if tracker_id in active_track_ids:
                state.missed_frames = 0
                continue
            state.missed_frames += 1
            if state.missed_frames > self.freeze_frames * 4:
                self._states.pop(tracker_id, None)

    @staticmethod
    def _remember(
        state: _IntegrityState,
        track: Track,
        world_position: tuple[float, float],
        timestamp_sec: float,
    ) -> None:
        state.previous_world = world_position
        state.previous_timestamp_sec = timestamp_sec
        state.previous_bbox = list(track.xyxy)
        state.previous_class_id = track.class_id

    @staticmethod
    def _bbox_jump_risk(
        previous: list[float],
        current: list[float],
    ) -> tuple[float, str | None]:
        px1, py1, px2, py2 = previous
        cx1, cy1, cx2, cy2 = current
        previous_w = max(px2 - px1, 1.0)
        previous_h = max(py2 - py1, 1.0)
        current_w = max(cx2 - cx1, 1.0)
        current_h = max(cy2 - cy1, 1.0)
        size_ratio = max(current_w * current_h, previous_w * previous_h) / max(
            min(current_w * current_h, previous_w * previous_h),
            1.0,
        )
        aspect_ratio_delta = abs((current_w / current_h) - (previous_w / previous_h))
        center_shift = math.dist(
            ((px1 + px2) / 2.0, (py1 + py2) / 2.0),
            ((cx1 + cx2) / 2.0, (cy1 + cy2) / 2.0),
        )
        if size_ratio > 4.0:
            return 0.85, "bbox_size_jump"
        if aspect_ratio_delta > 1.5:
            return 0.8, "bbox_aspect_ratio_jump"
        if center_shift > max(previous_w, previous_h) * 3.0:
            return 0.8, "bbox_center_jump"
        return 0.0, None
