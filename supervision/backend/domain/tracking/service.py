from __future__ import annotations

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


class TrackingService:
    def __init__(
        self,
        frame_rate: float = 30.0,
        track_buffer: int = 30,
        matching_threshold: float = 0.3,
        iou_threshold: float | None = None,
        max_center_distance: float = 50.0,
    ) -> None:
        self.frame_rate = frame_rate
        self.track_buffer = track_buffer
        self.matching_threshold = iou_threshold if iou_threshold is not None else matching_threshold
        self.max_center_distance = max_center_distance
        self._next_tracker_id = 1
        self._active_tracks: dict[int, Track] = {}

    def update(self, detections: Detections) -> list[Track]:
        unmatched_tracks = set(self._active_tracks)
        updated: dict[int, Track] = {}

        for detection in detections.items:
            matched_track = self._best_match(detection, unmatched_tracks)
            if matched_track is None:
                track = detection.to_track(
                    self._next_tracker_id,
                    frame_index=detections.frame_index,
                )
                self._next_tracker_id += 1
            else:
                unmatched_tracks.remove(matched_track.tracker_id)
                track = matched_track.with_detection(
                    xyxy=detection.xyxy,
                    confidence=detection.confidence,
                    frame_index=detections.frame_index,
                )
            updated[track.tracker_id] = track

        for tracker_id in unmatched_tracks:
            track = self._active_tracks[tracker_id]
            if detections.frame_index - track.last_seen_frame <= self.track_buffer:
                updated[tracker_id] = track

        self._active_tracks = updated
        return list(updated.values())

    def get_active_tracks(self) -> list[Track]:
        return list(self._active_tracks.values())

    def reset(self) -> None:
        self._next_tracker_id = 1
        self._active_tracks.clear()

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
