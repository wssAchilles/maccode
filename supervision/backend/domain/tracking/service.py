from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from domain.detection.models import Detection, Detections
from domain.tracking.models import Track


def bbox_iou(left: list[float], right: list[float]) -> float:
    left_x1, left_y1, left_x2, left_y2 = left
    right_x1, right_y1, right_x2, right_y2 = right
    inter_x1 = max(left_x1, right_x1)
    inter_y1 = max(left_y1, right_y1)
    inter_x2 = min(left_x2, right_x2)
    inter_y2 = min(left_y2, right_y2)
    inter_w = max(0.0, inter_x2 - inter_x1)
    inter_h = max(0.0, inter_y2 - inter_y1)
    intersection = inter_w * inter_h
    left_area = max(0.0, left_x2 - left_x1) * max(0.0, left_y2 - left_y1)
    right_area = max(0.0, right_x2 - right_x1) * max(0.0, right_y2 - right_y1)
    union = left_area + right_area - intersection
    return intersection / union if union > 0 else 0.0


@dataclass(frozen=True)
class TrackingDiagnostics:
    association_match_count: int = 0
    low_score_recovery_count: int = 0
    unmatched_track_count: int = 0
    new_track_count: int = 0
    fragmentation_count: int = 0
    fallback_used: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "association_match_count": self.association_match_count,
            "low_score_recovery_count": self.low_score_recovery_count,
            "unmatched_track_count": self.unmatched_track_count,
            "new_track_count": self.new_track_count,
            "fragmentation_count": self.fragmentation_count,
            "fallback_used": self.fallback_used,
        }


class TrackingService:
    def __init__(
        self,
        frame_rate: float = 30.0,
        track_buffer: int = 30,
        matching_threshold: float = 0.3,
        iou_threshold: float | None = None,
        max_center_distance: float = 50.0,
        high_confidence_threshold: float = 0.45,
        low_confidence_threshold: float = 0.15,
    ) -> None:
        self.frame_rate = frame_rate
        self.track_buffer = track_buffer
        self.matching_threshold = iou_threshold if iou_threshold is not None else matching_threshold
        self.max_center_distance = max_center_distance
        self.high_confidence_threshold = high_confidence_threshold
        self.low_confidence_threshold = low_confidence_threshold
        self._next_tracker_id = 1
        self._active_tracks: dict[int, Track] = {}
        self._last_diagnostics = TrackingDiagnostics()

    def update(self, detections: Detections) -> list[Track]:
        try:
            from scipy.optimize import linear_sum_assignment  # type: ignore[import-not-found]
        except ImportError:
            return self._update_greedy(detections, fallback_used=True)
        return self._update_global(detections, linear_sum_assignment)

    @property
    def diagnostics(self) -> TrackingDiagnostics:
        return self._last_diagnostics

    def diagnostics_dict(self) -> dict[str, object]:
        return self._last_diagnostics.to_dict()

    def get_active_tracks(self) -> list[Track]:
        return list(self._active_tracks.values())

    def reset(self) -> None:
        self._next_tracker_id = 1
        self._active_tracks.clear()
        self._last_diagnostics = TrackingDiagnostics()

    def _update_global(self, detections: Detections, linear_sum_assignment: Any) -> list[Track]:
        unmatched_tracks = set(self._active_tracks)
        updated: dict[int, Track] = {}
        high_confidence = [
            detection
            for detection in detections.items
            if detection.confidence >= self.high_confidence_threshold
        ]
        low_confidence = [
            detection
            for detection in detections.items
            if (
                self.low_confidence_threshold
                <= detection.confidence
                < self.high_confidence_threshold
            )
        ]

        matched_high, used_high = self._match_detection_stage(
            high_confidence,
            unmatched_tracks,
            detections.frame_index,
            linear_sum_assignment,
            low_score_recovered=False,
        )
        updated.update(matched_high)
        matched_low, _ = self._match_detection_stage(
            low_confidence,
            unmatched_tracks,
            detections.frame_index,
            linear_sum_assignment,
            low_score_recovered=True,
        )
        updated.update(matched_low)

        new_track_count = 0
        for index, detection in enumerate(high_confidence):
            if index in used_high:
                continue
            track = detection.to_track(
                self._next_tracker_id,
                frame_index=detections.frame_index,
            )
            self._next_tracker_id += 1
            updated[track.tracker_id] = track
            new_track_count += 1

        stale_count = 0
        for tracker_id in list(unmatched_tracks):
            track = self._active_tracks[tracker_id]
            if detections.frame_index - track.last_seen_frame <= self.track_buffer:
                updated[tracker_id] = track
            else:
                stale_count += 1

        self._active_tracks = updated
        self._last_diagnostics = TrackingDiagnostics(
            association_match_count=len(matched_high) + len(matched_low),
            low_score_recovery_count=len(matched_low),
            unmatched_track_count=len(unmatched_tracks),
            new_track_count=new_track_count,
            fragmentation_count=stale_count,
            fallback_used=False,
        )
        return list(updated.values())

    def _update_greedy(
        self,
        detections: Detections,
        *,
        fallback_used: bool = False,
    ) -> list[Track]:
        unmatched_tracks = set(self._active_tracks)
        updated: dict[int, Track] = {}
        match_count = 0
        new_track_count = 0

        for detection in detections.items:
            if detection.confidence < self.high_confidence_threshold:
                continue
            matched_track = self._best_match(detection, unmatched_tracks)
            if matched_track is None:
                track = detection.to_track(
                    self._next_tracker_id,
                    frame_index=detections.frame_index,
                )
                self._next_tracker_id += 1
                new_track_count += 1
            else:
                unmatched_tracks.remove(matched_track.tracker_id)
                match_count += 1
                track = matched_track.with_detection(
                    xyxy=detection.xyxy,
                    confidence=detection.confidence,
                    frame_index=detections.frame_index,
                )
            updated[track.tracker_id] = track

        stale_count = 0
        for tracker_id in unmatched_tracks:
            track = self._active_tracks[tracker_id]
            if detections.frame_index - track.last_seen_frame <= self.track_buffer:
                updated[tracker_id] = track
            else:
                stale_count += 1

        self._active_tracks = updated
        self._last_diagnostics = TrackingDiagnostics(
            association_match_count=match_count,
            low_score_recovery_count=0,
            unmatched_track_count=len(unmatched_tracks),
            new_track_count=new_track_count,
            fragmentation_count=stale_count,
            fallback_used=fallback_used,
        )
        return list(updated.values())

    def _match_detection_stage(
        self,
        detections: list[Detection],
        unmatched_tracks: set[int],
        frame_index: int,
        linear_sum_assignment: Any,
        *,
        low_score_recovered: bool,
    ) -> tuple[dict[int, Track], set[int]]:
        if not detections or not unmatched_tracks:
            return {}, set()
        track_ids = list(unmatched_tracks)
        cost_matrix = [
            [
                self._association_cost(self._active_tracks[tracker_id], detection)
                for detection in detections
            ]
            for tracker_id in track_ids
        ]
        row_indices, col_indices = linear_sum_assignment(cost_matrix)
        matched: dict[int, Track] = {}
        used_detection_indices: set[int] = set()
        for row, col in zip(row_indices, col_indices, strict=False):
            tracker_id = track_ids[int(row)]
            detection = detections[int(col)]
            track = self._active_tracks[tracker_id]
            cost = float(cost_matrix[int(row)][int(col)])
            if cost > self._maximum_match_cost(track, detection, low_score_recovered):
                continue
            unmatched_tracks.remove(tracker_id)
            used_detection_indices.add(int(col))
            matched[tracker_id] = replace(
                track.with_detection(
                    xyxy=detection.xyxy,
                    confidence=detection.confidence,
                    frame_index=frame_index,
                ),
                association_quality=max(0.0, min(1.0, 1.0 - cost)),
                low_score_recovered=low_score_recovered,
            )
        return matched, used_detection_indices

    def _association_cost(self, track: Track, detection: Detection) -> float:
        if track.class_id != detection.class_id:
            return 1e6
        iou_distance = 1.0 - bbox_iou(track.xyxy, detection.xyxy)
        center_distance = min(
            self._center_distance(track, detection) / max(self.max_center_distance, 1.0),
            1.0,
        )
        size_delta = self._size_delta(track.xyxy, detection.xyxy)
        confidence_penalty = 1.0 - detection.confidence
        return (
            0.45 * iou_distance
            + 0.25 * center_distance
            + 0.15 * size_delta
            + 0.10 * confidence_penalty
        )

    def _maximum_match_cost(
        self,
        track: Track,
        detection: Detection,
        low_score_recovered: bool,
    ) -> float:
        if track.class_id != detection.class_id:
            return 0.0
        base = max(0.15, min(0.95, 1.0 - self.matching_threshold * 0.5))
        return base + (0.12 if low_score_recovered else 0.0)

    def _best_match(self, detection: Detection, candidates: set[int]) -> Track | None:
        best_track: Track | None = None
        best_score = 0.0
        closest_track: Track | None = None
        closest_distance = float("inf")
        for tracker_id in candidates:
            track = self._active_tracks[tracker_id]
            if track.class_id != detection.class_id:
                continue
            score = bbox_iou(track.xyxy, detection.xyxy)
            if score > best_score:
                best_score = score
                best_track = track
            distance = self._center_distance(track, detection)
            if distance < closest_distance:
                closest_distance = distance
                closest_track = track
        if best_score >= self.matching_threshold:
            return best_track
        if closest_distance <= self.max_center_distance:
            return closest_track
        return None

    @staticmethod
    def _center_distance(track: Track, detection: Detection) -> float:
        track_x, track_y = track.center
        detection_x, detection_y = detection.center
        return ((track_x - detection_x) ** 2 + (track_y - detection_y) ** 2) ** 0.5

    @staticmethod
    def _size_delta(left: list[float], right: list[float]) -> float:
        left_w = max(left[2] - left[0], 1.0)
        left_h = max(left[3] - left[1], 1.0)
        right_w = max(right[2] - right[0], 1.0)
        right_h = max(right[3] - right[1], 1.0)
        return min(
            (
                abs(left_w - right_w) / max(left_w, right_w)
                + abs(left_h - right_h) / max(left_h, right_h)
            )
            / 2.0,
            1.0,
        )
