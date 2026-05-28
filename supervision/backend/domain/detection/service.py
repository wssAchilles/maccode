from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from shared.exceptions.errors import InferenceError, ModelLoadError

from domain.detection.models import Detections

RawPrediction = dict[str, object]
Predictor = Callable[[object], Sequence[RawPrediction]]


class DetectionService:
    def __init__(
        self,
        model_path: str,
        device: str = "mps",
        confidence_threshold: float = 0.25,
        iou_threshold: float = 0.45,
        allowed_class_ids: set[int] | None = None,
        predictor: Predictor | None = None,
    ) -> None:
        self.model_path = model_path
        self.device = device
        self.confidence_threshold = confidence_threshold
        self.iou_threshold = iou_threshold
        self.allowed_class_ids = allowed_class_ids
        self._predictor = predictor
        self._model: Any | None = None

    def detect(
        self,
        frame: object,
        frame_index: int = 0,
        timestamp_sec: float = 0.0,
    ) -> Detections:
        try:
            raw_items = self._predict(frame)
        except Exception as exc:  # pragma: no cover - external model path
            raise InferenceError(str(exc)) from exc
        return Detections.from_raw(
            raw_items,
            frame_index=frame_index,
            timestamp_sec=timestamp_sec,
            confidence_threshold=self.confidence_threshold,
            allowed_class_ids=self.allowed_class_ids,
        )

    def get_class_names(self) -> dict[int, str]:
        model = self._load_model()
        names = getattr(model, "names", {})
        return {int(key): str(value) for key, value in dict(names).items()}

    def _predict(self, frame: object) -> Sequence[RawPrediction]:
        if self._predictor is not None:
            return self._predictor(frame)

        model = self._load_model()
        results = model(
            frame,
            device=self.device,
            conf=self.confidence_threshold,
            iou=self.iou_threshold,
        )
        return self._from_ultralytics_result(results[0])

    def _load_model(self) -> Any:
        if self._model is None:
            try:
                from ultralytics import YOLO  # type: ignore[import-not-found]
            except Exception as exc:  # pragma: no cover - depends on optional package
                raise ModelLoadError(
                    "ultralytics is required for real YOLO inference; use a predictor for tests"
                ) from exc
            self._model = YOLO(self.model_path)
        return self._model

    @staticmethod
    def _from_ultralytics_result(result: Any) -> list[RawPrediction]:
        names = getattr(result, "names", {})
        boxes = getattr(result, "boxes", None)
        if boxes is None:
            return []

        raw_items: list[RawPrediction] = []
        for xyxy, conf, cls in zip(
            boxes.xyxy.tolist(),
            boxes.conf.tolist(),
            boxes.cls.tolist(),
            strict=True,
        ):
            class_id = int(cls)
            raw_items.append(
                {
                    "xyxy": [float(value) for value in xyxy],
                    "confidence": float(conf),
                    "class_id": class_id,
                    "class_name": str(names.get(class_id, class_id)),
                }
            )
        return raw_items
