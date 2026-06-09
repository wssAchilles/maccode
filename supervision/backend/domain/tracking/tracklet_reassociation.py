from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TrackletAssociation:
    child_id: int
    parent_id: int
    score: float
    rejection_reason: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "child_id": self.child_id,
            "parent_id": self.parent_id,
            "association_score": self.score,
            "association_rejection_reason": self.rejection_reason,
        }


@dataclass(frozen=True)
class TrackletReassociationSummary:
    candidate_count: int
    relinked_count: int
    rejected_count: int
    rejected_reason_counts: dict[str, int] | None = None
    model_reference: str = "ocsort_strongsort_geometry_tracklet_reassociation_v1"

    def to_dict(self) -> dict[str, object]:
        return {
            "candidate_count": self.candidate_count,
            "relinked_count": self.relinked_count,
            "rejected_count": self.rejected_count,
            "rejected_reason_counts": self.rejected_reason_counts or {},
            "model_reference": self.model_reference,
            "paper_alignment": [
                "OC-SORT observation-centric short-gap repair",
                "StrongSORT AFLink/GSI-style tracklet reconnect",
            ],
        }


class TrackletReAssociationService:
    """Offline OC-SORT/StrongSORT-style linker using BEV kinematics and class gates."""

    max_gap_frames = 5
    max_gap_seconds = 2.0
    max_position_error_m = 8.0
    max_speed_delta_kmh = 45.0
    max_id_switch_risk = 0.7
    min_relinked_speed_uncertainty_kmh = 3.0
    max_relinked_speed_uncertainty_kmh = 18.0

    def relink_reports(
        self,
        reports: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], TrackletReassociationSummary]:
        endpoints = self._track_endpoints(reports)
        all_candidates: list[TrackletAssociation] = []
        candidates = 0
        for child_id, child in endpoints.items():
            for parent_id, parent in endpoints.items():
                if parent_id == child_id:
                    continue
                candidate = self._score(parent_id, parent, child_id, child)
                if candidate is None:
                    continue
                candidates += 1
                all_candidates.append(candidate)
        candidates_by_score = [
            candidate for candidate in all_candidates if candidate.score >= 0.62
        ]
        rejected_reason_counts = self._rejected_reason_counts(
            all_candidates,
            candidates_by_score,
        )
        associations = self._one_to_one_associations(candidates_by_score)
        self._add_one_to_one_rejections(
            rejected_reason_counts,
            candidates_by_score,
            associations,
        )
        if not associations:
            return reports, TrackletReassociationSummary(
                candidates,
                0,
                candidates,
                dict(sorted(rejected_reason_counts.items())),
            )
        updated = [self._copy_report(report) for report in reports]
        association_by_child = {item.child_id: item for item in associations}
        for report in updated:
            for track in report.get("active_tracks", []):
                if not isinstance(track, dict):
                    continue
                association = association_by_child.get(int(track.get("tracker_id", -1)))
                if association is None:
                    continue
                track["tracklet_relinked"] = True
                track["tracklet_parent_id"] = association.parent_id
                track["association_score"] = association.score
                track["recovery_score"] = association.score
                track["tracklet_relink_reason"] = (
                    association.rejection_reason or "bev_kinematic_reconnect"
                )
                track["association_rejection_reason"] = association.rejection_reason
                track["id_switch_risk"] = max(
                    float(track.get("id_switch_risk") or 0.0),
                    max(0.0, 1.0 - association.score),
                )
                if track.get("speed_kmh") is not None:
                    track["speed_source"] = (
                        track.get("speed_source")
                        or "tracklet_reassociated_bev_kinematic"
                    )
                    track["speed_uncertainty_kmh"] = self._relinked_uncertainty(
                        track.get("speed_uncertainty_kmh"),
                        association.score,
                    )
        return updated, TrackletReassociationSummary(
            candidate_count=candidates,
            relinked_count=len(associations),
            rejected_count=max(0, candidates - len(associations)),
            rejected_reason_counts=dict(sorted(rejected_reason_counts.items())),
        )

    @staticmethod
    def _one_to_one_associations(
        candidates: list[TrackletAssociation],
    ) -> list[TrackletAssociation]:
        selected: list[TrackletAssociation] = []
        used_children: set[int] = set()
        used_parents: set[int] = set()
        for candidate in sorted(candidates, key=lambda item: item.score, reverse=True):
            if (
                candidate.child_id in used_children
                or candidate.parent_id in used_parents
            ):
                continue
            selected.append(candidate)
            used_children.add(candidate.child_id)
            used_parents.add(candidate.parent_id)
        return selected

    @staticmethod
    def _rejected_reason_counts(
        all_candidates: list[TrackletAssociation],
        accepted_candidates: list[TrackletAssociation],
    ) -> Counter[str]:
        accepted_pairs = {
            (candidate.child_id, candidate.parent_id) for candidate in accepted_candidates
        }
        counts: Counter[str] = Counter()
        for candidate in all_candidates:
            if (candidate.child_id, candidate.parent_id) in accepted_pairs:
                continue
            counts[candidate.rejection_reason or "score_threshold"] += 1
        return counts

    @staticmethod
    def _add_one_to_one_rejections(
        counts: Counter[str],
        candidates: list[TrackletAssociation],
        associations: list[TrackletAssociation],
    ) -> None:
        associated_pairs = {
            (association.child_id, association.parent_id) for association in associations
        }
        for candidate in candidates:
            if (candidate.child_id, candidate.parent_id) not in associated_pairs:
                counts["one_to_one_conflict"] += 1

    def _relinked_uncertainty(self, current: object, score: float) -> float:
        score_uncertainty = self.min_relinked_speed_uncertainty_kmh + (
            (1.0 - max(0.0, min(1.0, score))) * 10.0
        )
        try:
            current_uncertainty = float(current)
        except (TypeError, ValueError):
            current_uncertainty = 0.0
        return round(
            max(
                self.min_relinked_speed_uncertainty_kmh,
                min(
                    self.max_relinked_speed_uncertainty_kmh,
                    max(current_uncertainty, score_uncertainty),
                ),
            ),
            6,
        )

    def _score(
        self,
        parent_id: int,
        parent: dict[str, Any],
        child_id: int,
        child: dict[str, Any],
    ) -> TrackletAssociation | None:
        if parent["class_id"] != child["class_id"]:
            return None
        if (
            float(parent.get("id_switch_risk") or 0.0) >= self.max_id_switch_risk
            or float(child.get("id_switch_risk") or 0.0) >= self.max_id_switch_risk
        ):
            return TrackletAssociation(child_id, parent_id, 0.0, "id_switch_risk_gate")
        gap_frames = int(child["first_frame"]) - int(parent["last_frame"])
        gap_sec = float(child["first_time"]) - float(parent["last_time"])
        if gap_frames <= 0 or gap_frames > self.max_gap_frames or gap_sec > self.max_gap_seconds:
            return None
        predicted = (
            float(parent["last_x"]) + float(parent["vx"]) * gap_sec,
            float(parent["last_y"]) + float(parent["vy"]) * gap_sec,
        )
        observed = (float(child["first_x"]), float(child["first_y"]))
        error = math.dist(predicted, observed)
        if error > self.max_position_error_m:
            return TrackletAssociation(child_id, parent_id, 0.0, "bev_position_gate")
        speed_delta = abs(float(parent["speed"]) - float(child["speed"]))
        if speed_delta > self.max_speed_delta_kmh:
            return TrackletAssociation(child_id, parent_id, 0.0, "speed_jump_gate")
        direction_score = self._direction_score(parent, child)
        lane_score = self._lane_consistency_score(parent, child)
        score = (
            0.48 * max(0.0, 1.0 - error / self.max_position_error_m)
            + 0.24 * direction_score
            + 0.18 * max(0.0, 1.0 - speed_delta / 25.0)
            + 0.10 * lane_score
        )
        return TrackletAssociation(
            child_id=child_id,
            parent_id=parent_id,
            score=round(score, 6),
        )

    @staticmethod
    def _direction_score(parent: dict[str, Any], child: dict[str, Any]) -> float:
        parent_v = (float(parent["vx"]), float(parent["vy"]))
        child_v = (float(child["vx"]), float(child["vy"]))
        parent_norm = math.hypot(*parent_v)
        child_norm = math.hypot(*child_v)
        if parent_norm < 1e-6 or child_norm < 1e-6:
            return 0.5
        cosine = (
            parent_v[0] * child_v[0] + parent_v[1] * child_v[1]
        ) / (parent_norm * child_norm)
        return max(0.0, min(1.0, (cosine + 1.0) / 2.0))

    @staticmethod
    def _lane_consistency_score(parent: dict[str, Any], child: dict[str, Any]) -> float:
        parent_plane = parent.get("plane_id")
        child_plane = child.get("plane_id")
        if parent_plane and child_plane and parent_plane != child_plane:
            return 0.0
        parent_heading = parent.get("heading_deg")
        child_heading = child.get("heading_deg")
        if parent_heading is None or child_heading is None:
            return 0.7
        diff = abs((float(parent_heading) - float(child_heading) + 180.0) % 360.0 - 180.0)
        return max(0.0, min(1.0, 1.0 - diff / 90.0))

    @staticmethod
    def _track_endpoints(reports: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
        grouped: dict[int, list[dict[str, Any]]] = {}
        for report_index, report in enumerate(reports):
            frame_index = TrackletReAssociationService._report_frame_index(
                report,
                report_index,
            )
            timestamp = TrackletReAssociationService._report_timestamp_sec(
                report,
                frame_index,
            )
            for track in report.get("active_tracks", []):
                if not isinstance(track, dict):
                    continue
                if track.get("ground_x_m") is None or track.get("ground_y_m") is None:
                    continue
                item = dict(track)
                item["_frame_index"] = frame_index
                item["_timestamp_sec"] = timestamp
                grouped.setdefault(int(track.get("tracker_id", -1)), []).append(item)
        endpoints: dict[int, dict[str, Any]] = {}
        for tracker_id, tracks in grouped.items():
            ordered = sorted(tracks, key=lambda item: int(item["_frame_index"]))
            if len(ordered) < 2:
                continue
            first = ordered[0]
            last = ordered[-1]
            max_id_switch_risk = max(
                float(track.get("id_switch_risk") or 0.0) for track in ordered
            )
            endpoints[tracker_id] = {
                "class_id": int(first.get("class_id", -1)),
                "first_frame": int(first["_frame_index"]),
                "last_frame": int(last["_frame_index"]),
                "first_time": float(first["_timestamp_sec"]),
                "last_time": float(last["_timestamp_sec"]),
                "first_x": float(first["ground_x_m"]),
                "first_y": float(first["ground_y_m"]),
                "last_x": float(last["ground_x_m"]),
                "last_y": float(last["ground_y_m"]),
                "vx": float(last.get("velocity_x_mps") or 0.0),
                "vy": float(last.get("velocity_y_mps") or 0.0),
                "speed": float(last.get("speed_kmh") or 0.0),
                "heading_deg": last.get("heading_deg"),
                "plane_id": last.get("plane_id"),
                "id_switch_risk": max_id_switch_risk,
            }
        return endpoints

    @staticmethod
    def _report_frame_index(report: dict[str, Any], report_index: int) -> int:
        try:
            return int(report.get("frame_index", report_index))
        except (TypeError, ValueError):
            return report_index

    @staticmethod
    def _report_timestamp_sec(report: dict[str, Any], frame_index: int) -> float:
        try:
            return float(report["timestamp_sec"])
        except (KeyError, TypeError, ValueError):
            return frame_index / 30.0

    @staticmethod
    def _copy_report(report: dict[str, Any]) -> dict[str, Any]:
        copied = dict(report)
        copied["active_tracks"] = [
            dict(track) if isinstance(track, dict) else track
            for track in report.get("active_tracks", [])
        ]
        return copied
