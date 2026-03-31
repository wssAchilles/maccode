from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from app.config import settings
from app.ports import (
    StrategyOrchestrationEntry,
    StrategyOrchestrationSnapshot,
)


class StrategyOrchestrationStateStorePort(Protocol):
    @property
    def backend_name(self) -> str: ...

    async def load_state(self) -> dict[str, Any] | None: ...

    async def save_state(self, state: dict[str, Any]) -> None: ...


@dataclass(slots=True)
class _MutableStrategyEntry:
    strategy_id: str
    label: str
    engine: str
    source: str
    role: str
    enabled: bool
    priority: int
    observe_weight: float
    primary_weight: float
    symbol_coverage: tuple[str, ...]
    metadata: dict[str, Any]


class RuntimeStrategyOrchestrationManager:
    def __init__(
        self,
        *,
        state_store: StrategyOrchestrationStateStorePort | None = None,
    ) -> None:
        self._state_store = state_store
        self._state_restored = False
        self._state = self._default_state()

    async def startup(self) -> None:
        if self._state_store is None:
            return
        payload = await self._state_store.load_state()
        if payload is None:
            await self._state_store.save_state(self._serialize_state())
            return
        self._state = self._merge_state(payload)
        self._state_restored = True
        await self._state_store.save_state(self._serialize_state())

    async def shutdown(self) -> None:
        if self._state_store is None:
            return
        await self._state_store.save_state(self._serialize_state())

    def snapshot(
        self,
        *,
        tracked_symbols: tuple[str, ...],
        inference_runtime_enabled: bool,
        inference_model_symbols: tuple[str, ...] = (),
        inference_engine_name: str | None = None,
    ) -> StrategyOrchestrationSnapshot:
        normalized_symbols = tuple(dict.fromkeys(symbol for symbol in tracked_symbols if symbol))
        default_inference_coverage = inference_model_symbols or normalized_symbols
        entries: list[StrategyOrchestrationEntry] = []
        for entry in self._state["entries"]:
            coverage = tuple(entry.symbol_coverage)
            if entry.source == "rule_engine":
                resolved_coverage = normalized_symbols if not coverage else _filter_coverage(coverage, normalized_symbols)
                enabled = entry.enabled
                engine = entry.engine or settings.inference_engine_name
            else:
                resolved_coverage = (
                    _filter_coverage(coverage, normalized_symbols)
                    if coverage
                    else _filter_coverage(default_inference_coverage, normalized_symbols)
                )
                enabled = entry.enabled and inference_runtime_enabled
                engine = inference_engine_name or entry.engine or settings.inference_engine_name
            entries.append(
                StrategyOrchestrationEntry(
                    strategy_id=entry.strategy_id,
                    label=entry.label,
                    engine=engine,
                    source=entry.source,
                    role=entry.role,
                    enabled=enabled,
                    priority=entry.priority,
                    observe_weight=entry.observe_weight,
                    primary_weight=entry.primary_weight,
                    symbol_coverage=resolved_coverage,
                    metadata={
                        **dict(entry.metadata),
                        "state_backend": self._state_store.backend_name if self._state_store is not None else None,
                        "state_restored": self._state_restored,
                    },
                )
            )
        return StrategyOrchestrationSnapshot(
            conflict_policy=self._state["conflict_policy"],
            downgrade_policy=self._state["downgrade_policy"],
            tracked_symbols=normalized_symbols,
            state_backend=self._state_store.backend_name if self._state_store is not None else None,
            state_restored=self._state_restored,
            entries=tuple(entries),
        )

    def _default_state(self) -> dict[str, Any]:
        return {
            "conflict_policy": settings.strategy_conflict_policy,
            "downgrade_policy": settings.strategy_downgrade_policy,
            "entries": [
                _MutableStrategyEntry(
                    strategy_id="default",
                    label="Rule engine",
                    engine="moving_average",
                    source="rule_engine",
                    role="baseline",
                    enabled=settings.strategy_rule_enabled,
                    priority=settings.strategy_rule_priority,
                    observe_weight=settings.strategy_rule_weight_observe,
                    primary_weight=settings.strategy_rule_weight_primary,
                    symbol_coverage=_normalize_symbol_list(settings.strategy_rule_symbol_coverage),
                    metadata={"configured_source": "settings"},
                ),
                _MutableStrategyEntry(
                    strategy_id="inference",
                    label="Inference model",
                    engine=settings.inference_engine_name,
                    source="inference",
                    role="adaptive",
                    enabled=settings.strategy_inference_enabled,
                    priority=settings.strategy_inference_priority,
                    observe_weight=settings.strategy_inference_weight_observe,
                    primary_weight=settings.strategy_inference_weight_primary,
                    symbol_coverage=_normalize_symbol_list(settings.strategy_inference_symbol_coverage),
                    metadata={"configured_source": "settings"},
                ),
            ],
        }

    def _serialize_state(self) -> dict[str, Any]:
        return {
            "conflict_policy": self._state["conflict_policy"],
            "downgrade_policy": self._state["downgrade_policy"],
            "entries": [
                {
                    "strategy_id": entry.strategy_id,
                    "label": entry.label,
                    "engine": entry.engine,
                    "source": entry.source,
                    "role": entry.role,
                    "enabled": entry.enabled,
                    "priority": entry.priority,
                    "observe_weight": entry.observe_weight,
                    "primary_weight": entry.primary_weight,
                    "symbol_coverage": list(entry.symbol_coverage),
                    "metadata": dict(entry.metadata),
                }
                for entry in self._state["entries"]
            ],
        }

    def _merge_state(self, payload: dict[str, Any]) -> dict[str, Any]:
        default_state = self._default_state()
        default_entries = {
            entry.strategy_id: entry
            for entry in default_state["entries"]
        }
        loaded_entries = payload.get("entries")
        if not isinstance(loaded_entries, list):
            loaded_entries = []
        merged_entries: list[_MutableStrategyEntry] = []
        for default_entry in default_entries.values():
            loaded = next(
                (
                    item
                    for item in loaded_entries
                    if isinstance(item, dict) and item.get("strategy_id") == default_entry.strategy_id
                ),
                None,
            )
            merged_entries.append(
                _MutableStrategyEntry(
                    strategy_id=default_entry.strategy_id,
                    label=_coerce_text(loaded, "label", default_entry.label),
                    engine=_coerce_text(loaded, "engine", default_entry.engine),
                    source=default_entry.source,
                    role=_coerce_text(loaded, "role", default_entry.role),
                    enabled=_coerce_bool(loaded, "enabled", default_entry.enabled),
                    priority=max(_coerce_int(loaded, "priority", default_entry.priority), 1),
                    observe_weight=max(_coerce_float(loaded, "observe_weight", default_entry.observe_weight), 0.0),
                    primary_weight=max(_coerce_float(loaded, "primary_weight", default_entry.primary_weight), 0.0),
                    symbol_coverage=_coerce_symbol_coverage(loaded, default_entry.symbol_coverage),
                    metadata=_coerce_metadata(loaded, default_entry.metadata),
                )
            )
        return {
            "conflict_policy": _coerce_policy(
                payload.get("conflict_policy"),
                default_state["conflict_policy"],
                allowed={"review_on_conflict", "prefer_priority", "prefer_weighted_score"},
            ),
            "downgrade_policy": _coerce_policy(
                payload.get("downgrade_policy"),
                default_state["downgrade_policy"],
                allowed={"review", "hold"},
            ),
            "entries": merged_entries,
        }


def _normalize_symbol_list(value: str) -> tuple[str, ...]:
    if not value.strip():
        return ()
    if value.strip() == "*":
        return ()
    return tuple(dict.fromkeys(item.strip().upper() for item in value.split(",") if item.strip()))


def _filter_coverage(coverage: tuple[str, ...], tracked_symbols: tuple[str, ...]) -> tuple[str, ...]:
    if not coverage:
        return tracked_symbols
    tracked = set(tracked_symbols)
    filtered = tuple(symbol for symbol in coverage if symbol in tracked)
    return filtered or tracked_symbols


def _coerce_text(payload: dict[str, Any] | None, key: str, default: str) -> str:
    if not payload:
        return default
    value = payload.get(key)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return default


def _coerce_bool(payload: dict[str, Any] | None, key: str, default: bool) -> bool:
    if not payload:
        return default
    value = payload.get(key)
    if isinstance(value, bool):
        return value
    return default


def _coerce_int(payload: dict[str, Any] | None, key: str, default: int) -> int:
    if not payload:
        return default
    value = payload.get(key)
    if isinstance(value, int):
        return value
    return default


def _coerce_float(payload: dict[str, Any] | None, key: str, default: float) -> float:
    if not payload:
        return default
    value = payload.get(key)
    if isinstance(value, (int, float)):
        return float(value)
    return default


def _coerce_symbol_coverage(
    payload: dict[str, Any] | None,
    default: tuple[str, ...],
) -> tuple[str, ...]:
    if not payload:
        return default
    raw = payload.get("symbol_coverage")
    if not isinstance(raw, list):
        return default
    values = [str(item).strip().upper() for item in raw if str(item).strip()]
    if values == ["*"]:
        return ()
    return tuple(dict.fromkeys(values))


def _coerce_metadata(payload: dict[str, Any] | None, default: dict[str, Any]) -> dict[str, Any]:
    if not payload:
        return dict(default)
    value = payload.get("metadata")
    if isinstance(value, dict):
        return dict(value)
    return dict(default)


def _coerce_policy(value: Any, default: str, *, allowed: set[str]) -> str:
    if isinstance(value, str) and value in allowed:
        return value
    return default
