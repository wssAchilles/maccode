from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ContactEpisodeSnapshot:
    episode_id: int
    phase: str
    start_timestamp_sec: float
    end_timestamp_sec: float
    touchdown_time_sec: float | None
    support_world: list[float]
    body_world: list[float]
    confidence: float
    foot_skate_risk: float

    def to_dict(self) -> dict[str, object]:
        return {
            "episode_id": self.episode_id,
            "phase": self.phase,
            "start_timestamp_sec": self.start_timestamp_sec,
            "end_timestamp_sec": self.end_timestamp_sec,
            "touchdown_time_sec": self.touchdown_time_sec,
            "support_world": list(self.support_world),
            "body_world": list(self.body_world),
            "confidence": self.confidence,
            "foot_skate_risk": self.foot_skate_risk,
        }


@dataclass(frozen=True)
class ContactEpisodeResult:
    contact_episodes: list[dict[str, object]]
    current_episode_id: int | None
    current_episode_phase: str | None
    support_velocity_mps: float | None
    support_zero_velocity_residual_mps: float | None
    speed_periodic_kmh: float | None
    body_periodic_speed_gap_kmh: float | None
    near_far_speed_drift_score: float | None
    geometry_status: str


@dataclass
class _MutableEpisode:
    episode_id: int
    phase: str
    start_timestamp_sec: float
    end_timestamp_sec: float
    touchdown_time_sec: float | None
    support_world: tuple[float, float]
    body_world: tuple[float, float]
    confidence_sum: float
    sample_count: int
    foot_skate_risk: float

    def update(
        self,
        *,
        timestamp_sec: float,
        phase: str,
        support_world: tuple[float, float],
        body_world: tuple[float, float],
        confidence: float,
        foot_skate_risk: float,
    ) -> None:
        self.phase = phase
        self.end_timestamp_sec = timestamp_sec
        self.support_world = support_world
        self.body_world = body_world
        self.confidence_sum += confidence
        self.sample_count += 1
        self.foot_skate_risk = max(self.foot_skate_risk, foot_skate_risk)

    def snapshot(self) -> ContactEpisodeSnapshot:
        return ContactEpisodeSnapshot(
            episode_id=self.episode_id,
            phase=self.phase,
            start_timestamp_sec=self.start_timestamp_sec,
            end_timestamp_sec=self.end_timestamp_sec,
            touchdown_time_sec=self.touchdown_time_sec,
            support_world=[float(self.support_world[0]), float(self.support_world[1])],
            body_world=[float(self.body_world[0]), float(self.body_world[1])],
            confidence=float(self.confidence_sum / max(self.sample_count, 1)),
            foot_skate_risk=float(self.foot_skate_risk),
        )


@dataclass
class _TrackEpisodeState:
    next_episode_id: int = 1
    current: _MutableEpisode | None = None
    completed: list[ContactEpisodeSnapshot] = field(default_factory=list)
    previous_support_world: tuple[float, float] | None = None
    previous_timestamp_sec: float | None = None
    previous_body_world: tuple[float, float] | None = None


class ContactEpisodeBuffer:
    """Convert frame-level contact phase probabilities into walking contact episodes."""

    def __init__(self, max_completed: int = 6) -> None:
        self.max_completed = max_completed
        self._states: dict[int, _TrackEpisodeState] = {}

    def update(
        self,
        *,
        tracker_id: int,
        timestamp_sec: float,
        body_world: tuple[float, float],
        support_world: tuple[float, float],
        contact_phase_probabilities: dict[str, float] | None,
        contact_confidence: float,
        foot_skate_risk: float,
        speed_body_kmh: float | None,
        near_far_metrics: dict[str, float | None] | None,
    ) -> ContactEpisodeResult:
        state = self._states.setdefault(tracker_id, _TrackEpisodeState())
        phase = self._dominant_phase(contact_phase_probabilities)
        support_velocity = self._support_velocity(
            state,
            support_world=support_world,
            timestamp_sec=timestamp_sec,
        )
        is_contact_phase = self._is_contact_phase(phase, contact_phase_probabilities)
        if is_contact_phase:
            self._update_contact_episode(
                state,
                phase=phase,
                timestamp_sec=timestamp_sec,
                body_world=body_world,
                support_world=support_world,
                confidence=contact_confidence,
                foot_skate_risk=foot_skate_risk,
            )
        else:
            self._close_current(state)
        periodic_speed = self._periodic_speed_kmh(state)
        speed_gap = (
            abs(float(speed_body_kmh) - periodic_speed)
            if speed_body_kmh is not None and periodic_speed is not None
            else None
        )
        drift_score = self._near_far_drift_score(near_far_metrics)
        geometry_status = self._geometry_status(
            support_velocity=support_velocity if is_contact_phase else None,
            foot_skate_risk=foot_skate_risk,
            periodic_speed_kmh=periodic_speed,
            body_periodic_speed_gap_kmh=speed_gap,
            near_far_speed_drift_score=drift_score,
        )
        state.previous_support_world = support_world
        state.previous_body_world = body_world
        state.previous_timestamp_sec = timestamp_sec
        snapshots = [episode.to_dict() for episode in state.completed[-self.max_completed :]]
        if state.current is not None:
            snapshots.append(state.current.snapshot().to_dict())
        return ContactEpisodeResult(
            contact_episodes=snapshots,
            current_episode_id=state.current.episode_id if state.current is not None else None,
            current_episode_phase=state.current.phase if state.current is not None else phase,
            support_velocity_mps=support_velocity,
            support_zero_velocity_residual_mps=support_velocity,
            speed_periodic_kmh=periodic_speed,
            body_periodic_speed_gap_kmh=speed_gap,
            near_far_speed_drift_score=drift_score,
            geometry_status=geometry_status,
        )

    @staticmethod
    def _dominant_phase(contact_phase_probabilities: dict[str, float] | None) -> str:
        if not contact_phase_probabilities:
            return "unknown"
        return max(contact_phase_probabilities.items(), key=lambda item: float(item[1]))[0]

    @staticmethod
    def _is_contact_phase(
        phase: str,
        contact_phase_probabilities: dict[str, float] | None,
    ) -> bool:
        probabilities = contact_phase_probabilities or {}
        return (
            phase in {"touchdown", "stance", "double_support"}
            and max(float(probabilities.get(phase, 0.0)), 0.0) >= 0.35
        )

    def _update_contact_episode(
        self,
        state: _TrackEpisodeState,
        *,
        phase: str,
        timestamp_sec: float,
        body_world: tuple[float, float],
        support_world: tuple[float, float],
        confidence: float,
        foot_skate_risk: float,
    ) -> None:
        if state.current is None:
            state.current = _MutableEpisode(
                episode_id=state.next_episode_id,
                phase=phase,
                start_timestamp_sec=timestamp_sec,
                end_timestamp_sec=timestamp_sec,
                touchdown_time_sec=timestamp_sec if phase == "touchdown" else None,
                support_world=support_world,
                body_world=body_world,
                confidence_sum=max(0.0, min(1.0, confidence)),
                sample_count=1,
                foot_skate_risk=max(0.0, min(1.0, foot_skate_risk)),
            )
            state.next_episode_id += 1
            return
        state.current.update(
            timestamp_sec=timestamp_sec,
            phase=phase,
            body_world=body_world,
            support_world=support_world,
            confidence=max(0.0, min(1.0, confidence)),
            foot_skate_risk=max(0.0, min(1.0, foot_skate_risk)),
        )

    def _close_current(self, state: _TrackEpisodeState) -> None:
        if state.current is None:
            return
        state.completed.append(state.current.snapshot())
        if len(state.completed) > self.max_completed:
            state.completed = state.completed[-self.max_completed :]
        state.current = None

    @staticmethod
    def _support_velocity(
        state: _TrackEpisodeState,
        *,
        support_world: tuple[float, float],
        timestamp_sec: float,
    ) -> float | None:
        if state.previous_support_world is None or state.previous_timestamp_sec is None:
            return None
        delta_t = timestamp_sec - state.previous_timestamp_sec
        if delta_t <= 0.0:
            return None
        return float(math.dist(state.previous_support_world, support_world) / delta_t)

    @staticmethod
    def _periodic_speed_kmh(state: _TrackEpisodeState) -> float | None:
        reliable = [
            episode
            for episode in state.completed
            if episode.confidence >= 0.45 and episode.foot_skate_risk <= 0.5
        ]
        if len(reliable) < 2:
            return None
        first = reliable[-2]
        last = reliable[-1]
        delta_t = last.start_timestamp_sec - first.start_timestamp_sec
        if delta_t <= 1e-3:
            return None
        distance_m = math.dist(first.support_world, last.support_world)
        return float(distance_m / delta_t * 3.6)

    @staticmethod
    def _near_far_drift_score(
        near_far_metrics: dict[str, float | None] | None,
    ) -> float | None:
        if near_far_metrics is None:
            return None
        values: list[float] = []
        for key in ("speed_local_scale_correlation", "speed_inverse_height_correlation"):
            value = near_far_metrics.get(key)
            if isinstance(value, int | float) and math.isfinite(float(value)):
                values.append(abs(float(value)))
        ratio = near_far_metrics.get("far_near_speed_ratio")
        if isinstance(ratio, int | float) and math.isfinite(float(ratio)):
            values.append(abs(float(ratio) - 1.0))
        return float(max(values)) if values else None

    @staticmethod
    def _geometry_status(
        *,
        support_velocity: float | None,
        foot_skate_risk: float,
        periodic_speed_kmh: float | None,
        body_periodic_speed_gap_kmh: float | None,
        near_far_speed_drift_score: float | None,
    ) -> str:
        if foot_skate_risk >= 0.6 or (support_velocity is not None and support_velocity > 0.6):
            return "foot_skate_invalid"
        if body_periodic_speed_gap_kmh is not None and body_periodic_speed_gap_kmh > max(
            2.5,
            (periodic_speed_kmh or 0.0) * 0.45,
        ):
            return "periodic_inconsistent"
        if near_far_speed_drift_score is not None and near_far_speed_drift_score > 0.4:
            return "weak_scale"
        return "accepted"
