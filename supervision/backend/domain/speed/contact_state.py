from __future__ import annotations

from dataclasses import dataclass

from domain.speed.ground_contact import GroundContactPoint

CONTACT_STATES = {
    "unknown",
    "left_stance",
    "right_stance",
    "double_support",
    "swing",
    "transition_touchdown",
    "transition_toeoff",
    "occluded",
    "bbox_polluted",
    "bicycle_push",
}


@dataclass(frozen=True)
class ContactStateResult:
    contact_state: str
    measurement_policy: str
    state_probabilities: dict[str, float]
    contact_phase_probabilities: dict[str, float]
    measurement_confidence_multiplier: float
    pixel_sigma_multiplier: float
    diagnostics: dict[str, object]


@dataclass(frozen=True)
class _TrackContactMemory:
    contact_state: str
    timestamp_sec: float


class PedestrianContactStateEstimator:
    """Heuristic foot-ground contact policy for monocular pedestrian speed."""

    def __init__(self) -> None:
        self._states: dict[int, _TrackContactMemory] = {}

    def assess(
        self,
        *,
        tracker_id: int,
        class_id: int,
        bbox_xyxy: list[float],
        contact_point: GroundContactPoint,
        timestamp_sec: float,
        person_bicycle_overlap: float = 0.0,
    ) -> ContactStateResult:
        if class_id != 0:
            return ContactStateResult(
                contact_state=contact_point.contact_state or "unknown",
                measurement_policy="update",
                state_probabilities={"unknown": 1.0},
                contact_phase_probabilities={"unknown": 1.0},
                measurement_confidence_multiplier=1.0,
                pixel_sigma_multiplier=1.0,
                diagnostics={"person_bicycle_overlap": person_bicycle_overlap},
            )

        bbox_height = max(float(bbox_xyxy[3] - bbox_xyxy[1]), 1.0)
        bbox_width = max(float(bbox_xyxy[2] - bbox_xyxy[0]), 1.0)
        aspect_ratio = bbox_width / bbox_height
        bbox_bottom = ((bbox_xyxy[0] + bbox_xyxy[2]) / 2.0, bbox_xyxy[3])
        foot_delta_px = (
            (contact_point.pixel[0] - bbox_bottom[0]) ** 2
            + (contact_point.pixel[1] - bbox_bottom[1]) ** 2
        ) ** 0.5
        source = (contact_point.measurement_source or contact_point.source).lower()
        bbox_polluted = bool(
            person_bicycle_overlap >= 0.08
            or aspect_ratio > 0.85
            or ("bbox" in source and contact_point.confidence < 0.45)
        )
        if person_bicycle_overlap >= 0.08:
            base_state = "bicycle_push"
        elif bbox_polluted:
            base_state = "bbox_polluted"
        elif "pose" in source and (contact_point.contact_state or "").endswith("stance"):
            base_state = contact_point.contact_state or "double_support"
        elif contact_point.contact_state in CONTACT_STATES:
            base_state = contact_point.contact_state or "unknown"
        elif "flow" in source and (contact_point.optical_flow_inlier_ratio or 0.0) >= 0.55:
            base_state = "double_support"
        else:
            base_state = "unknown"

        previous = self._states.get(tracker_id)
        state = self._transition_state(previous.contact_state if previous else None, base_state)
        policy = self._measurement_policy(state)
        confidence_multiplier, sigma_multiplier = self._policy_weights(policy)
        probabilities = self._probabilities(state)
        phase_probabilities = self._phase_probabilities(state, probabilities)
        self._states[tracker_id] = _TrackContactMemory(state, timestamp_sec)
        return ContactStateResult(
            contact_state=state,
            measurement_policy=policy,
            state_probabilities=probabilities,
            contact_phase_probabilities=phase_probabilities,
            measurement_confidence_multiplier=confidence_multiplier,
            pixel_sigma_multiplier=sigma_multiplier,
            diagnostics={
                "bbox_bottom_contact_delta_px": float(foot_delta_px),
                "bbox_aspect_ratio": float(aspect_ratio),
                "person_bicycle_overlap": float(person_bicycle_overlap),
                "bbox_polluted": bbox_polluted,
                "contact_measurement_policy": policy,
            },
        )

    @staticmethod
    def _transition_state(previous: str | None, current: str) -> str:
        stance_states = {"left_stance", "right_stance", "double_support"}
        if current in {"bbox_polluted", "bicycle_push", "occluded"}:
            return current
        if current in stance_states and previous in {None, "unknown", "swing"}:
            return "transition_touchdown"
        if current in {"unknown", "swing"} and previous in stance_states:
            return "transition_toeoff"
        return current

    @staticmethod
    def _measurement_policy(state: str) -> str:
        if state == "transition_touchdown":
            return "event_update"
        if state == "double_support":
            return "update"
        if state in {"left_stance", "right_stance", "unknown", "transition_toeoff"}:
            return "downweight"
        if state in {"swing", "occluded"}:
            return "predict_only"
        if state in {"bbox_polluted", "bicycle_push"}:
            return "reject"
        return "downweight"

    @staticmethod
    def _policy_weights(policy: str) -> tuple[float, float]:
        if policy == "event_update":
            return (1.0, 0.85)
        if policy == "update":
            return (0.85, 1.15)
        if policy == "downweight":
            return (0.45, 2.0)
        if policy == "predict_only":
            return (0.2, 3.0)
        if policy == "reject":
            return (0.1, 4.0)
        return (0.45, 2.0)

    @staticmethod
    def _probabilities(state: str) -> dict[str, float]:
        probabilities = {
            "left_stance": 0.0,
            "right_stance": 0.0,
            "double_support": 0.0,
            "swing": 0.0,
            "unknown": 0.0,
        }
        if state in {"left_stance", "transition_touchdown"}:
            probabilities["left_stance"] = 0.65
            probabilities["double_support"] = 0.2
        elif state == "right_stance":
            probabilities["right_stance"] = 0.65
            probabilities["double_support"] = 0.2
        elif state == "double_support":
            probabilities["double_support"] = 0.75
        elif state in {"swing", "transition_toeoff"}:
            probabilities["swing"] = 0.7
        else:
            probabilities["unknown"] = 1.0
        return probabilities

    @staticmethod
    def _phase_probabilities(
        state: str,
        contact_probabilities: dict[str, float],
    ) -> dict[str, float]:
        stance = max(
            float(contact_probabilities.get("left_stance", 0.0)),
            float(contact_probabilities.get("right_stance", 0.0)),
        )
        double_support = float(contact_probabilities.get("double_support", 0.0))
        swing = float(contact_probabilities.get("swing", 0.0))
        touchdown = 0.8 if state == "transition_touchdown" else 0.0
        toeoff = 0.8 if state == "transition_toeoff" else 0.0
        unknown = float(contact_probabilities.get("unknown", 0.0))
        total = max(stance + double_support + swing + touchdown + toeoff + unknown, 1e-9)
        return {
            "stance": stance / total,
            "double_support": double_support / total,
            "swing": swing / total,
            "touchdown": touchdown / total,
            "toeoff": toeoff / total,
            "unknown": unknown / total,
        }
