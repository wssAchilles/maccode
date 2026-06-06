from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from domain.speed.ground_contact import GroundContactPoint
from domain.tracking.models import Track


@dataclass(frozen=True)
class PoseGroundContactEstimator:
    model_path: str
    device: str
    _model: Any = field(default=None, init=False, repr=False, compare=False)

    def estimate(self, frame_image: object, track: Track) -> GroundContactPoint | None:
        if track.class_id != 0:
            return None
        try:
            model = self._load_model()
        except (ImportError, RuntimeError):
            return None
        try:
            results = model.predict(frame_image, device=self.device, verbose=False)
        except Exception:  # noqa: BLE001
            return None
        best_point: tuple[float, float] | None = None
        best_confidence = 0.0
        for result in results:
            keypoints = getattr(result, "keypoints", None)
            boxes = getattr(result, "boxes", None)
            if keypoints is None or boxes is None:
                continue
            keypoint_xy = getattr(keypoints, "xy", None)
            keypoint_conf = getattr(keypoints, "conf", None)
            box_xyxy = getattr(boxes, "xyxy", None)
            if keypoint_xy is None or keypoint_conf is None or box_xyxy is None:
                continue
            for index, candidate_box in enumerate(box_xyxy.cpu().numpy().tolist()):
                if self._iou(candidate_box, track.xyxy) < 0.25:
                    continue
                xy_values = keypoint_xy[index].cpu().numpy().tolist()
                conf_values = keypoint_conf[index].cpu().numpy().tolist()
                ankles = [
                    (xy_values[15], conf_values[15]),
                    (xy_values[16], conf_values[16]),
                ]
                valid = [(point, conf) for point, conf in ankles if conf >= 0.25]
                if not valid:
                    continue
                x = sum(point[0] * conf for point, conf in valid) / sum(conf for _, conf in valid)
                y = sum(point[1] * conf for point, conf in valid) / sum(conf for _, conf in valid)
                confidence = min(1.0, sum(conf for _, conf in valid) / len(valid))
                if confidence > best_confidence:
                    best_point = (float(x), float(y))
                    best_confidence = float(confidence)
        if best_point is None:
            return None
        return GroundContactPoint(
            pixel=best_point,
            raw_pixel=best_point,
            confidence=best_confidence,
            source="pose_ankle_ground_contact",
            observation_sigma_px=max(1.0, 3.0 / max(best_confidence, 0.1)),
            measurement_source="pose_ankle_ground_contact",
        )

    def _load_model(self) -> Any:
        model = self._model
        if model is not None:
            return model
        try:
            from ultralytics import YOLO  # type: ignore[import-not-found]
        except ImportError as exc:
            raise ImportError("ultralytics is required for pose ground contact") from exc
        model = YOLO(self.model_path)
        object.__setattr__(self, "_model", model)
        return model

    @staticmethod
    def _iou(left: list[float], right: list[float]) -> float:
        lx1, ly1, lx2, ly2 = left
        rx1, ry1, rx2, ry2 = right
        ix1 = max(lx1, rx1)
        iy1 = max(ly1, ry1)
        ix2 = min(lx2, rx2)
        iy2 = min(ly2, ry2)
        intersection = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
        left_area = max(0.0, lx2 - lx1) * max(0.0, ly2 - ly1)
        right_area = max(0.0, rx2 - rx1) * max(0.0, ry2 - ry1)
        union = left_area + right_area - intersection
        return intersection / union if union > 0 else 0.0
