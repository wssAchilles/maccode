from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
from typing import Any

import numpy as np

from app.config import settings
from app.infrastructure.inference_artifacts import LoadedInferenceArtifacts
from app.infrastructure.inference_features import SymbolFeatureBuffer
from app.ports import InferenceDecision, InferenceEngineStatus, RegisteredModel
from app.schemas import TickEvent
from app.signal_engine_service import SignalEngineService


class DisabledInferenceEngine:
    async def infer_signal(
        self,
        *,
        symbol: str,
        price: float,
        quantity: float,
        event_time: str,
    ) -> InferenceDecision | None:
        del symbol, price, quantity, event_time
        return None

    async def status(self) -> InferenceEngineStatus:
        return InferenceEngineStatus(
            enabled=False,
            ready=False,
            engine="disabled",
            mode="disabled",
            reason="inference disabled",
        )


class MovingAverageInferenceEngine:
    def __init__(
        self,
        *,
        engine_name: str,
        mode: str,
        model: RegisteredModel,
        fast_window: int,
        slow_window: int,
    ) -> None:
        self._engine_name = engine_name
        self._mode = mode
        self._model = model
        self._signal_engine = SignalEngineService(
            fast_window=fast_window,
            slow_window=slow_window,
        )

    async def infer_signal(
        self,
        *,
        symbol: str,
        price: float,
        quantity: float,
        event_time: str,
    ) -> InferenceDecision | None:
        signal, _ = self._signal_engine.evaluate_tick(
            TickEvent(
                symbol=symbol,
                price=price,
                quantity=quantity,
                event_time=event_time,
            )
        )
        return InferenceDecision(
            strategy_id=signal.strategy_id,
            signal=signal.signal,
            confidence=signal.confidence,
            engine=self._engine_name,
            model_id=self._model.model_id,
            model_version=self._model.version,
            metadata={
                "model_source": self._model.source,
                "task": self._model.task,
            },
        )

    async def status(self) -> InferenceEngineStatus:
        return InferenceEngineStatus(
            enabled=True,
            ready=True,
            engine=self._engine_name,
            mode=self._mode,
            metadata={
                "fast_window": settings.fast_window,
                "slow_window": settings.slow_window,
            },
        )


@dataclass(frozen=True, slots=True)
class StaticModelRegistry:
    models: tuple[RegisteredModel, ...]
    active_model_id: str | None = None

    def list_models(self) -> tuple[RegisteredModel, ...]:
        return self.models

    def active_model(self) -> RegisteredModel | None:
        if not self.models:
            return None
        if self.active_model_id is None:
            return self.models[0]
        for model in self.models:
            if model.model_id == self.active_model_id:
                return model
        return None


class OnnxInferenceEngine:
    def __init__(
        self,
        *,
        engine_name: str,
        mode: str,
        model: RegisteredModel,
        artifacts: LoadedInferenceArtifacts,
        session: Any | None = None,
    ) -> None:
        self._engine_name = engine_name
        self._mode = mode
        self._model = model
        self._artifacts = artifacts
        self._session = session or self._create_session(artifacts.onnx_path)
        self._feature_mean = np.asarray(artifacts.preprocessing.feature_mean, dtype=np.float32)
        self._feature_std = np.asarray(
            [value if abs(value) > 1e-12 else 1.0 for value in artifacts.preprocessing.feature_std],
            dtype=np.float32,
        )
        self._label_to_signal = {
            int(index): str(signal_name)
            for index, signal_name in artifacts.manifest.get("signals", {}).items()
        }
        self._strategy_id = str(artifacts.manifest.get("strategy_id", "inference"))
        self._buffers = {
            symbol: SymbolFeatureBuffer(
                feature_columns=artifacts.preprocessing.feature_columns,
                lookback=artifacts.preprocessing.lookback,
            )
            for symbol in artifacts.preprocessing.symbol_to_id
        }

    async def infer_signal(
        self,
        *,
        symbol: str,
        price: float,
        quantity: float,
        event_time: str,
    ) -> InferenceDecision | None:
        del event_time
        symbol_id = self._artifacts.preprocessing.symbol_to_id.get(symbol)
        if symbol_id is None:
            return None
        buffer = self._buffers[symbol]
        feature_window = buffer.update(price=price, quantity=quantity)
        if feature_window is None:
            return None

        normalized = (feature_window - self._feature_mean) / self._feature_std
        outputs = self._session.run(
            None,
            {
                "features": np.expand_dims(normalized.astype(np.float32), axis=0),
                "symbol_ids": np.asarray([symbol_id], dtype=np.int64),
            },
        )
        logits = np.asarray(outputs[0], dtype=np.float32)[0]
        probabilities = self._softmax(logits)
        predicted_index = int(np.argmax(probabilities))
        return InferenceDecision(
            strategy_id=self._strategy_id,
            signal=self._label_to_signal[predicted_index],
            confidence=float(probabilities[predicted_index]),
            engine=self._engine_name,
            model_id=self._model.model_id,
            model_version=self._model.version,
            metadata={
                "model_source": self._model.source,
                "task": self._model.task,
                "symbol_id": symbol_id,
                "warmup_ready": True,
            },
        )

    async def status(self) -> InferenceEngineStatus:
        warmed_symbols = sum(1 for buffer in self._buffers.values() if len(buffer.feature_rows) > 0)
        return InferenceEngineStatus(
            enabled=True,
            ready=True,
            engine=self._engine_name,
            mode=self._mode,
            metadata={
                "artifact_cache_dir": str(self._artifacts.cache_dir),
                "lookback": self._artifacts.preprocessing.lookback,
                "feature_columns": list(self._artifacts.preprocessing.feature_columns),
                "tracked_symbols": list(self._artifacts.preprocessing.symbol_to_id.keys()),
                "warmed_symbols": warmed_symbols,
            },
        )

    @staticmethod
    def _create_session(onnx_path: Path) -> Any:
        import onnxruntime as ort

        return ort.InferenceSession(
            onnx_path.as_posix(),
            providers=["CPUExecutionProvider"],
        )

    @staticmethod
    def _softmax(logits: np.ndarray) -> np.ndarray:
        shifted = logits - np.max(logits)
        exponent = np.exp(shifted)
        total = np.sum(exponent)
        if not math.isfinite(float(total)) or total <= 0:
            return np.ones_like(logits) / len(logits)
        return exponent / total
