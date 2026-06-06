from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from domain.speed.ground_contact import GroundContactPoint
from domain.speed.view_transformer import ViewTransformer


@dataclass(frozen=True)
class OpticalFlowObservation:
    velocity_mps: tuple[float, float]
    confidence: float
    tracked_points: int


class OpticalFlowVelocityEstimator:
    def __init__(self, view_transformer: ViewTransformer) -> None:
        self.view_transformer = view_transformer

    def estimate(
        self,
        previous_frame: object,
        current_frame: object,
        previous_xyxy: list[float],
        previous_contact_point: tuple[float, float],
        delta_t_sec: float,
    ) -> OpticalFlowObservation | None:
        if delta_t_sec <= 0:
            return None
        pixel_observation = self._pixel_flow_observation(
            previous_frame,
            current_frame,
            previous_xyxy,
        )
        if pixel_observation is None:
            return None
        median_displacement, confidence, tracked_points = pixel_observation
        contact_end = (
            previous_contact_point[0] + float(median_displacement[0]),
            previous_contact_point[1] + float(median_displacement[1]),
        )
        world_start = self.view_transformer.transform_point(*previous_contact_point)
        world_end = self.view_transformer.transform_point(*contact_end)
        velocity = (
            (world_end[0] - world_start[0]) / delta_t_sec,
            (world_end[1] - world_start[1]) / delta_t_sec,
        )
        return OpticalFlowObservation(
            velocity_mps=(float(velocity[0]), float(velocity[1])),
            confidence=float(confidence),
            tracked_points=int(tracked_points),
        )

    def refine_contact_point(
        self,
        previous_frame: object,
        current_frame: object,
        previous_xyxy: list[float],
        previous_contact_point: tuple[float, float],
    ) -> GroundContactPoint | None:
        pixel_observation = self._pixel_flow_observation(
            previous_frame,
            current_frame,
            previous_xyxy,
        )
        if pixel_observation is None:
            return None
        median_displacement, confidence, tracked_points = pixel_observation
        refined_pixel = (
            previous_contact_point[0] + float(median_displacement[0]),
            previous_contact_point[1] + float(median_displacement[1]),
        )
        return GroundContactPoint(
            pixel=refined_pixel,
            raw_pixel=refined_pixel,
            confidence=float(confidence),
            source="flow_refined_ground_contact",
            observation_sigma_px=max(0.75, 4.0 / max(tracked_points, 1)),
            measurement_source="flow_refined_ground_contact",
        )

    def _pixel_flow_observation(
        self,
        previous_frame: object,
        current_frame: object,
        previous_xyxy: list[float],
    ) -> tuple[np.ndarray, float, int] | None:
        try:
            import cv2  # type: ignore[import-not-found]
        except ImportError:
            return None
        cv2_module: Any = cv2

        previous_gray = self._to_gray(previous_frame, cv2_module)
        current_gray = self._to_gray(current_frame, cv2_module)
        if previous_gray is None or current_gray is None:
            return None

        points = self._feature_points(previous_gray, previous_xyxy, cv2_module)
        if points is None or len(points) < 3:
            return None

        next_points, status, _ = cv2_module.calcOpticalFlowPyrLK(
            previous_gray,
            current_gray,
            points,
            None,
            winSize=(21, 21),
            maxLevel=3,
            criteria=(
                cv2_module.TERM_CRITERIA_EPS | cv2_module.TERM_CRITERIA_COUNT,
                20,
                0.03,
            ),
        )
        if next_points is None or status is None:
            return None
        backward_points, backward_status, _ = cv2_module.calcOpticalFlowPyrLK(
            current_gray,
            previous_gray,
            next_points,
            None,
            winSize=(21, 21),
            maxLevel=3,
            criteria=(
                cv2_module.TERM_CRITERIA_EPS | cv2_module.TERM_CRITERIA_COUNT,
                20,
                0.03,
            ),
        )
        if backward_points is None or backward_status is None:
            return None
        forward_backward_error = np.linalg.norm(
            backward_points.reshape(-1, 2) - points.reshape(-1, 2),
            axis=1,
        )
        valid_mask = (
            (status.reshape(-1) == 1)
            & (backward_status.reshape(-1) == 1)
            & (forward_backward_error <= 2.5)
        )
        if int(valid_mask.sum()) < 3:
            return None
        displacements = next_points.reshape(-1, 2)[valid_mask] - points.reshape(-1, 2)[valid_mask]
        median_displacement = np.median(displacements, axis=0)
        residuals = np.linalg.norm(displacements - median_displacement, axis=1)
        median_residual = float(np.median(residuals)) if len(residuals) else 0.0
        flow_px = float(np.linalg.norm(median_displacement))
        residual_factor = 1.0 / (1.0 + median_residual / max(flow_px, 1.0))
        point_factor = min(1.0, int(valid_mask.sum()) / 12.0)
        confidence = max(0.0, min(1.0, residual_factor * point_factor))
        return median_displacement, float(confidence), int(valid_mask.sum())

    @staticmethod
    def _to_gray(frame: object, cv2: Any) -> np.ndarray | None:
        array = np.asarray(frame)
        if array.ndim == 2:
            return array.astype(np.uint8, copy=False)
        if array.ndim == 3:
            return cv2.cvtColor(array, cv2.COLOR_BGR2GRAY)
        return None

    @staticmethod
    def _feature_points(
        gray: np.ndarray,
        xyxy: list[float],
        cv2: Any,
    ) -> np.ndarray | None:
        height, width = gray.shape[:2]
        x1, y1, x2, y2 = xyxy
        left = max(0, min(width - 1, int(round(x1))))
        right = max(left + 1, min(width, int(round(x2))))
        top = max(0, min(height - 1, int(round(y1 + (y2 - y1) * 0.35))))
        bottom = max(top + 1, min(height, int(round(y2))))
        roi = gray[top:bottom, left:right]
        if roi.size == 0:
            return None
        corners = cv2.goodFeaturesToTrack(
            roi,
            maxCorners=40,
            qualityLevel=0.01,
            minDistance=3,
            blockSize=3,
        )
        if corners is None:
            return None
        corners = corners.reshape(-1, 2)
        corners[:, 0] += left
        corners[:, 1] += top
        return corners.astype(np.float32).reshape(-1, 1, 2)
