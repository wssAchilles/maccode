from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np


class ProcessedVideoRenderer:
    def __init__(
        self,
        output_path: Path,
        frame_width: int,
        frame_height: int,
        fps: float,
        homography_grid: dict[str, object] | None = None,
    ) -> None:
        try:
            import cv2  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError("opencv-python is required to render processed videos") from exc

        self._cv2: Any = cv2
        self.output_path = output_path
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.homography_grid = homography_grid
        self._trail_history: dict[int, list[tuple[int, int]]] = {}
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self._writer = self._open_writer(output_path, fps)

    def render(self, frame_image: object, report: dict[str, Any]) -> None:
        frame = self._normalize_frame(frame_image)
        self._draw_homography_grid(frame)
        safety = report.get("safety_metrics") or {}
        speeding_ids = set(safety.get("speeding_track_ids") or [])
        violation_ids = set(safety.get("red_light_violation_track_ids") or [])
        for track in report.get("active_tracks", []):
            self._draw_track(frame, track, speeding_ids, violation_ids)
        self._writer.write(frame)

    def close(self) -> None:
        self._writer.release()

    def _open_writer(self, output_path: Path, fps: float) -> Any:
        for codec in ("avc1", "mp4v"):
            fourcc = self._cv2.VideoWriter_fourcc(*codec)
            writer = self._cv2.VideoWriter(
                str(output_path),
                fourcc,
                max(fps, 1.0),
                (self.frame_width, self.frame_height),
            )
            if writer.isOpened():
                return writer
            writer.release()
        raise RuntimeError(f"could not open video writer for {output_path}")

    def _normalize_frame(self, frame_image: object) -> np.ndarray:
        frame = np.asarray(frame_image).copy()
        if frame.ndim == 2:
            frame = self._cv2.cvtColor(frame, self._cv2.COLOR_GRAY2BGR)
        if frame.shape[2] == 4:
            frame = self._cv2.cvtColor(frame, self._cv2.COLOR_BGRA2BGR)
        if frame.shape[1] != self.frame_width or frame.shape[0] != self.frame_height:
            frame = self._cv2.resize(frame, (self.frame_width, self.frame_height))
        return frame

    def _draw_homography_grid(self, frame: np.ndarray) -> None:
        if not self.homography_grid:
            return
        if self.homography_grid.get("calibration_trusted") is not True:
            return
        grid_layer = frame.copy()
        grid_lines = self.homography_grid.get("lines", [])
        if not isinstance(grid_lines, list):
            return
        for line in grid_lines:
            if not isinstance(line, dict):
                continue
            start = self._point(line.get("pixel_start"))
            end = self._point(line.get("pixel_end"))
            if start is None or end is None:
                continue
            self._draw_dashed_line(grid_layer, start, end, color=(210, 220, 230), thickness=2)
        self._cv2.addWeighted(grid_layer, 0.32, frame, 0.68, 0, dst=frame)

    def _draw_track(
        self,
        frame: np.ndarray,
        track: dict[str, Any],
        speeding_ids: set[int],
        violation_ids: set[int],
    ) -> None:
        tracker_id = int(track["tracker_id"])
        box = self._track_box(track)
        if box is None:
            return
        x1, y1, x2, y2 = box
        x1, y1 = self._clamp_point((x1, y1))
        x2, y2 = self._clamp_point((x2, y2))
        color = self._track_color(track, tracker_id, speeding_ids, violation_ids)
        bottom_center = ((x1 + x2) // 2, y2)
        self._trail_history.setdefault(tracker_id, []).append(bottom_center)
        self._trail_history[tracker_id] = self._trail_history[tracker_id][-20:]
        points = np.array(self._trail_history[tracker_id], dtype=np.int32)
        if len(points) >= 2:
            self._cv2.polylines(frame, [points], isClosed=False, color=(0, 190, 255), thickness=3)
        self._cv2.rectangle(frame, (x1, y1), (x2, y2), color, 3)
        if tracker_id in violation_ids:
            self._cv2.rectangle(frame, (x1 - 3, y1 - 3), (x2 + 3, y2 + 3), (0, 0, 255), 2)
        label = self._track_label(track, tracker_id)
        self._draw_label(frame, label, (x1, max(20, y1 - 8)), color)

    def _track_color(
        self,
        track: dict[str, Any],
        tracker_id: int,
        speeding_ids: set[int],
        violation_ids: set[int],
    ) -> tuple[int, int, int]:
        if tracker_id in violation_ids or tracker_id in speeding_ids:
            return (35, 35, 245)
        if int(track.get("class_id", -1)) == 0:
            return (70, 220, 90)
        return (245, 150, 65)

    @staticmethod
    def _track_label(track: dict[str, Any], tracker_id: int) -> str:
        class_name = str(track.get("class_name", "object"))
        speed = track.get("speed_kmh")
        physics_valid = bool(track.get("physics_valid", True))
        if speed is None or not physics_valid:
            speed_text = "N/A"
        else:
            speed_text = f"{float(speed):.1f} km/h"
        quality = None if physics_valid else str(track.get("quality_label") or "invalid")
        return f"#{tracker_id} {class_name} {speed_text}" + (
            f" {quality}" if quality else ""
        )

    @staticmethod
    def _track_box(track: dict[str, Any]) -> tuple[int, int, int, int] | None:
        xyxy = track.get("xyxy")
        if not isinstance(xyxy, (list, tuple)) or len(xyxy) != 4:
            return None
        try:
            x1, y1, x2, y2 = [int(round(float(value))) for value in xyxy]
        except (TypeError, ValueError):
            return None
        return x1, y1, x2, y2

    def _draw_label(
        self,
        frame: np.ndarray,
        label: str,
        origin: tuple[int, int],
        color: tuple[int, int, int],
    ) -> None:
        x, y = origin
        font = self._cv2.FONT_HERSHEY_SIMPLEX
        scale = 0.55
        thickness = 2
        (text_width, text_height), baseline = self._cv2.getTextSize(label, font, scale, thickness)
        x2 = min(self.frame_width - 1, x + text_width + 10)
        y1 = max(0, y - text_height - baseline - 8)
        self._cv2.rectangle(frame, (x, y1), (x2, y + 4), (10, 16, 28), -1)
        self._cv2.rectangle(frame, (x, y1), (x2, y + 4), color, 1)
        self._cv2.putText(frame, label, (x + 5, y - 4), font, scale, (240, 248, 255), thickness)

    def _draw_dashed_line(
        self,
        frame: np.ndarray,
        start: tuple[int, int],
        end: tuple[int, int],
        color: tuple[int, int, int],
        thickness: int,
        dash_length: int = 18,
        gap_length: int = 14,
    ) -> None:
        x1, y1 = start
        x2, y2 = end
        distance = float(((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5)
        if distance <= 0:
            return
        dx = (x2 - x1) / distance
        dy = (y2 - y1) / distance
        current = 0.0
        while current < distance:
            dash_end = min(current + dash_length, distance)
            p1 = (int(round(x1 + dx * current)), int(round(y1 + dy * current)))
            p2 = (int(round(x1 + dx * dash_end)), int(round(y1 + dy * dash_end)))
            self._cv2.line(frame, p1, p2, color, thickness)
            current += dash_length + gap_length

    def _point(self, value: object) -> tuple[int, int] | None:
        if not isinstance(value, (list, tuple)) or len(value) != 2:
            return None
        return self._clamp_point((int(round(float(value[0]))), int(round(float(value[1])))))

    def _clamp_point(self, point: tuple[int, int]) -> tuple[int, int]:
        x, y = point
        return (
            max(0, min(self.frame_width - 1, x)),
            max(0, min(self.frame_height - 1, y)),
        )
