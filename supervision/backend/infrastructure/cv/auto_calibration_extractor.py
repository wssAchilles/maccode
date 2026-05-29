from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

from domain.auto_calibration.models import CandidateLine


@dataclass(frozen=True)
class FrameGeometryEvidence:
    candidate_lines: list[CandidateLine]
    frame_index: int
    frame_width: int
    frame_height: int

    def to_dict(self) -> dict[str, object]:
        return {
            "frame_index": self.frame_index,
            "frame_width": self.frame_width,
            "frame_height": self.frame_height,
            "candidate_line_count": len(self.candidate_lines),
            "candidate_lines": [line.to_dict() for line in self.candidate_lines],
        }


class FrameGeometryExtractor:
    """Extract road-plane geometry candidates from video frames using OpenCV."""

    def __init__(
        self,
        max_lines: int = 12,
        canny_low: int = 60,
        canny_high: int = 160,
        hough_threshold: int = 55,
    ) -> None:
        self.max_lines = max_lines
        self.canny_low = canny_low
        self.canny_high = canny_high
        self.hough_threshold = hough_threshold

    def extract_from_video(
        self,
        video_path: Path,
        sample_frame_index: int = 0,
    ) -> FrameGeometryEvidence:
        try:
            import cv2  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover - environment guard
            raise RuntimeError("opencv-python is required for frame geometry extraction") from exc

        capture = cv2.VideoCapture(str(video_path))
        if not capture.isOpened():
            raise ValueError(f"could not open video: {video_path}")
        try:
            if sample_frame_index > 0:
                capture.set(cv2.CAP_PROP_POS_FRAMES, sample_frame_index)
            ok, frame = capture.read()
            if not ok:
                raise ValueError(f"could not read calibration frame from: {video_path}")
        finally:
            capture.release()
        return self.extract_from_image(frame, frame_index=sample_frame_index)

    def extract_from_image(self, image: object, frame_index: int = 0) -> FrameGeometryEvidence:
        try:
            import cv2  # type: ignore[import-not-found]
            import numpy as np
        except ImportError as exc:  # pragma: no cover - environment guard
            raise RuntimeError(
                "opencv-python and numpy are required for geometry extraction",
            ) from exc

        frame = np.asarray(image)
        if frame.ndim < 2:
            raise ValueError("image must have at least two dimensions")
        height, width = int(frame.shape[0]), int(frame.shape[1])
        if height <= 0 or width <= 0:
            raise ValueError("image must have positive dimensions")

        scale = min(1.0, 960.0 / max(width, height))
        working = frame
        if scale < 1.0:
            working = cv2.resize(frame, (int(width * scale), int(height * scale)))
        gray = cv2.cvtColor(working, cv2.COLOR_BGR2GRAY) if working.ndim == 3 else working
        gray = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(gray, self.canny_low, self.canny_high)
        min_line_length = max(24, int(min(edges.shape[:2]) * 0.08))
        max_line_gap = max(8, int(min(edges.shape[:2]) * 0.025))
        raw_lines = cv2.HoughLinesP(
            edges,
            rho=1,
            theta=math.pi / 180,
            threshold=self.hough_threshold,
            minLineLength=min_line_length,
            maxLineGap=max_line_gap,
        )
        if raw_lines is None:
            return FrameGeometryEvidence(
                candidate_lines=[],
                frame_index=frame_index,
                frame_width=width,
                frame_height=height,
            )

        candidates: list[tuple[float, CandidateLine]] = []
        for index, raw_line in enumerate(raw_lines[:, 0, :]):
            x1, y1, x2, y2 = (float(value) / scale for value in raw_line)
            line_length = math.hypot(x2 - x1, y2 - y1)
            if line_length < min(width, height) * 0.04:
                continue
            angle_deg = abs(math.degrees(math.atan2(y2 - y1, x2 - x1)))
            if angle_deg > 90.0:
                angle_deg = 180.0 - angle_deg
            if angle_deg < 8.0:
                kind = "frame_stop_or_crosswalk_line"
            elif angle_deg > 72.0:
                kind = "frame_vertical_edge"
            else:
                kind = "frame_lane_or_road_edge"
            bottom_weight = (max(y1, y2) / max(height, 1)) * 0.35
            score = line_length * (1.0 + bottom_weight)
            candidates.append(
                (
                    score,
                    CandidateLine(
                        name=f"frame_hough_{index:02d}",
                        start=(round(x1, 2), round(y1, 2)),
                        end=(round(x2, 2), round(y2, 2)),
                        kind=kind,
                    ),
                ),
            )

        selected = self._deduplicate_lines(candidates)
        return FrameGeometryEvidence(
            candidate_lines=selected[: self.max_lines],
            frame_index=frame_index,
            frame_width=width,
            frame_height=height,
        )

    @staticmethod
    def _deduplicate_lines(
        candidates: list[tuple[float, CandidateLine]],
    ) -> list[CandidateLine]:
        selected: list[CandidateLine] = []
        for _, line in sorted(candidates, key=lambda item: item[0], reverse=True):
            if any(
                FrameGeometryExtractor._line_too_similar(line, existing)
                for existing in selected
            ):
                continue
            selected.append(line)
        return selected

    @staticmethod
    def _line_too_similar(first: CandidateLine, second: CandidateLine) -> bool:
        first_mid = (
            (first.start[0] + first.end[0]) / 2.0,
            (first.start[1] + first.end[1]) / 2.0,
        )
        second_mid = (
            (second.start[0] + second.end[0]) / 2.0,
            (second.start[1] + second.end[1]) / 2.0,
        )
        midpoint_distance = math.hypot(first_mid[0] - second_mid[0], first_mid[1] - second_mid[1])
        first_angle = math.atan2(first.end[1] - first.start[1], first.end[0] - first.start[0])
        second_angle = math.atan2(second.end[1] - second.start[1], second.end[0] - second.start[0])
        angle_distance = abs((first_angle - second_angle + math.pi / 2) % math.pi - math.pi / 2)
        return midpoint_distance < 24.0 and angle_distance < math.radians(6)
