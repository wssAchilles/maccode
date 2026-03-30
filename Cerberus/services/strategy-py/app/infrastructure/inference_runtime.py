from __future__ import annotations

from dataclasses import dataclass, field
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


@dataclass(slots=True)
class StaticModelRegistry:
    models: tuple[RegisteredModel, ...]
    active_model_id: str | None = None
    active_model_version: str | None = None
    artifacts: dict[str, LoadedInferenceArtifacts] = field(default_factory=dict)

    def list_models(self) -> tuple[RegisteredModel, ...]:
        return self.models

    def active_model(self) -> RegisteredModel | None:
        if not self.models:
            return None
        if self.active_model_id is None:
            return self.models[0]
        for model in self.models:
            if model.model_id != self.active_model_id:
                continue
            if self.active_model_version is None or model.version == self.active_model_version:
                return model
        return self.models[0]

    def activate_model(self, *, model_id: str, version: str | None = None) -> RegisteredModel:
        for model in self.models:
            if model.model_id != model_id:
                continue
            if version is None or model.version == version:
                self.active_model_id = model.model_id
                self.active_model_version = model.version
                return model
        raise KeyError(f"unknown model: {model_id}:{version or '*'}")

    def active_artifacts(self) -> LoadedInferenceArtifacts | None:
        active_model = self.active_model()
        if active_model is None:
            return None
        return self.artifacts.get(_model_key(active_model))


@dataclass(slots=True)
class _OnnxRuntimeState:
    model: RegisteredModel
    artifacts: LoadedInferenceArtifacts
    session: Any
    feature_mean: np.ndarray
    feature_std: np.ndarray
    label_to_signal: dict[int, str]
    strategy_id: str
    buffers: dict[str, SymbolFeatureBuffer]


class OnnxInferenceEngine:
    def __init__(
        self,
        *,
        engine_name: str,
        mode: str,
        registry: StaticModelRegistry | None = None,
        model: RegisteredModel | None = None,
        artifacts: LoadedInferenceArtifacts | None = None,
        session: Any | None = None,
        session_factory: Any | None = None,
    ) -> None:
        self._engine_name = engine_name
        self._mode = mode
        if registry is None:
            if model is None or artifacts is None:
                raise TypeError(
                    "OnnxInferenceEngine requires either registry=... or model=... with artifacts=..."
                )
            registry = StaticModelRegistry(
                models=(model,),
                active_model_id=model.model_id,
                active_model_version=model.version,
                artifacts={_model_key(model): artifacts},
            )
        self._registry = registry
        self._session_factory = session_factory or (
            (lambda _onnx_path: session) if session is not None else self._create_session
        )
        self._runtime_states: dict[str, _OnnxRuntimeState] = {}

    async def infer_signal(
        self,
        *,
        symbol: str,
        price: float,
        quantity: float,
        event_time: str,
    ) -> InferenceDecision | None:
        del event_time
        runtime_state = self._active_runtime_state()
        if runtime_state is None:
            return None
        symbol_id = runtime_state.artifacts.preprocessing.symbol_to_id.get(symbol)
        if symbol_id is None:
            return None
        buffer = runtime_state.buffers[symbol]
        feature_window = buffer.update(price=price, quantity=quantity)
        if feature_window is None:
            return None

        normalized = (feature_window - runtime_state.feature_mean) / runtime_state.feature_std
        outputs = runtime_state.session.run(
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
            strategy_id=runtime_state.strategy_id,
            signal=runtime_state.label_to_signal[predicted_index],
            confidence=float(probabilities[predicted_index]),
            engine=self._engine_name,
            model_id=runtime_state.model.model_id,
            model_version=runtime_state.model.version,
            metadata={
                "model_source": runtime_state.model.source,
                "task": runtime_state.model.task,
                "symbol_id": symbol_id,
                "warmup_ready": True,
            },
        )

    async def status(self) -> InferenceEngineStatus:
        runtime_state = self._active_runtime_state()
        if runtime_state is None:
            return InferenceEngineStatus(
                enabled=False,
                ready=False,
                engine=self._engine_name,
                mode=self._mode,
                reason="no active onnx inference model",
            )
        warmed_symbols = sum(
            1 for buffer in runtime_state.buffers.values() if len(buffer.feature_rows) > 0
        )
        return InferenceEngineStatus(
            enabled=True,
            ready=True,
            engine=self._engine_name,
            mode=self._mode,
            metadata={
                "artifact_cache_dir": str(runtime_state.artifacts.cache_dir),
                "lookback": runtime_state.artifacts.preprocessing.lookback,
                "feature_columns": list(runtime_state.artifacts.preprocessing.feature_columns),
                "tracked_symbols": list(runtime_state.artifacts.preprocessing.symbol_to_id.keys()),
                "warmed_symbols": warmed_symbols,
            },
        )

    def _active_runtime_state(self) -> _OnnxRuntimeState | None:
        active_model = self._registry.active_model()
        active_artifacts = self._registry.active_artifacts()
        if active_model is None or active_artifacts is None:
            return None
        key = _model_key(active_model)
        runtime_state = self._runtime_states.get(key)
        if runtime_state is not None:
            return runtime_state
        runtime_state = _OnnxRuntimeState(
            model=active_model,
            artifacts=active_artifacts,
            session=self._session_factory(active_artifacts.onnx_path),
            feature_mean=np.asarray(active_artifacts.preprocessing.feature_mean, dtype=np.float32),
            feature_std=np.asarray(
                [
                    value if abs(value) > 1e-12 else 1.0
                    for value in active_artifacts.preprocessing.feature_std
                ],
                dtype=np.float32,
            ),
            label_to_signal={
                int(index): str(signal_name)
                for index, signal_name in active_artifacts.manifest.get("signals", {}).items()
            },
            strategy_id=str(active_artifacts.manifest.get("strategy_id", "inference")),
            buffers={
                symbol: SymbolFeatureBuffer(
                    feature_columns=active_artifacts.preprocessing.feature_columns,
                    lookback=active_artifacts.preprocessing.lookback,
                )
                for symbol in active_artifacts.preprocessing.symbol_to_id
            },
        )
        self._runtime_states[key] = runtime_state
        return runtime_state

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


def _model_key(model: RegisteredModel) -> str:
    return f"{model.model_id}:{model.version}"
