from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class TrafficLightStateResult:
    state: str
    confidence: float
    red_score: float
    yellow_score: float
    green_score: float

    def to_dict(self) -> dict[str, float | str]:
        return {
            "state": self.state,
            "confidence": self.confidence,
            "red_score": self.red_score,
            "yellow_score": self.yellow_score,
            "green_score": self.green_score,
        }


class TrafficLightStateEstimator:
    def estimate(
        self,
        frame_image: object,
        xyxy: list[float],
    ) -> TrafficLightStateResult:
        frame = np.asarray(frame_image)
        if frame.ndim != 3 or frame.shape[2] < 3:
            return self._unknown()
        height, width = frame.shape[:2]
        x1, y1, x2, y2 = self._clip_box(xyxy, width, height)
        if x2 <= x1 or y2 <= y1:
            return self._unknown()
        crop = frame[y1:y2, x1:x2, :3].astype(float)
        if crop.size == 0:
            return self._unknown()
        red_score = self._red_score(crop)
        yellow_score = self._yellow_score(crop)
        green_score = self._green_score(crop)
        scores = {
            "red": red_score,
            "yellow": yellow_score,
            "green": green_score,
        }
        state, score = max(scores.items(), key=lambda item: item[1])
        score_sum = red_score + yellow_score + green_score
        confidence = float(score / score_sum) if score_sum > 1e-9 else 0.0
        if score < 20.0 or confidence < 0.45:
            state = "unknown"
        return TrafficLightStateResult(
            state=state,
            confidence=confidence,
            red_score=float(red_score),
            yellow_score=float(yellow_score),
            green_score=float(green_score),
        )

    @staticmethod
    def _clip_box(
        xyxy: list[float],
        width: int,
        height: int,
    ) -> tuple[int, int, int, int]:
        x1, y1, x2, y2 = [int(round(value)) for value in xyxy]
        return (
            max(0, min(width - 1, x1)),
            max(0, min(height - 1, y1)),
            max(0, min(width, x2)),
            max(0, min(height, y2)),
        )

    @staticmethod
    def _red_score(crop: np.ndarray) -> float:
        b = crop[:, :, 0]
        g = crop[:, :, 1]
        r = crop[:, :, 2]
        return float(np.maximum(r - np.maximum(g, b), 0.0).mean())

    @staticmethod
    def _yellow_score(crop: np.ndarray) -> float:
        b = crop[:, :, 0]
        g = crop[:, :, 1]
        r = crop[:, :, 2]
        return float(np.maximum(np.minimum(r, g) - b, 0.0).mean())

    @staticmethod
    def _green_score(crop: np.ndarray) -> float:
        b = crop[:, :, 0]
        g = crop[:, :, 1]
        r = crop[:, :, 2]
        return float(np.maximum(g - np.maximum(r, b), 0.0).mean())

    @staticmethod
    def _unknown() -> TrafficLightStateResult:
        return TrafficLightStateResult(
            state="unknown",
            confidence=0.0,
            red_score=0.0,
            yellow_score=0.0,
            green_score=0.0,
        )
