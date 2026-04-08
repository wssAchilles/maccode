from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from app.ports import (
    InferenceAuditEvent,
    InferenceComparisonSnapshot,
    InferenceDecision,
    InferenceRolloutSnapshot,
    InferenceRolloutStateStorePort,
    InferenceSymbolComparison,
    RegisteredModel,
)


@dataclass(slots=True)
class _SymbolCounter:
    compared_ticks: int = 0
    agreement_count: int = 0
    divergence_count: int = 0

    def to_snapshot(self, *, symbol: str) -> InferenceSymbolComparison:
        return InferenceSymbolComparison(
            symbol=symbol,
            compared_ticks=self.compared_ticks,
            agreement_count=self.agreement_count,
            divergence_count=self.divergence_count,
        )


class RuntimeInferenceRolloutManager:
    def __init__(
        self,
        *,
        configured_mode: str,
        active_model: RegisteredModel | None,
        started_at: float,
        required_macro_f1: float,
        required_observe_ticks: int,
        required_agreement_ratio: float,
        force_primary: bool,
        max_audit_events: int = 50,
        state_store: InferenceRolloutStateStorePort | None = None,
        persist_every_observations: int = 25,
    ) -> None:
        self._configured_mode = configured_mode
        self._active_model = active_model
        self._required_macro_f1 = required_macro_f1
        self._required_observe_ticks = required_observe_ticks
        self._required_agreement_ratio = required_agreement_ratio
        self._force_primary = force_primary
        self._state_store = state_store
        self._persist_every_observations = max(persist_every_observations, 1)
        self._target_mode = configured_mode
        self._observed_ticks = 0
        self._compared_ticks = 0
        self._agreement_count = 0
        self._divergence_count = 0
        self._rule_signal_counts: Counter[str] = Counter()
        self._inference_signal_counts: Counter[str] = Counter()
        self._symbol_counters: dict[str, _SymbolCounter] = {}
        self._audit_events: deque[InferenceAuditEvent] = deque(maxlen=max_audit_events)
        self._emitted_milestones: set[int] = set()
        self._state_restored = False
        self._last_persisted_at = ""
        self._dirty_observations = 0
        self._last_state_error: str | None = None
        started_iso = _iso_from_timestamp(started_at)
        self._started_at = started_iso
        self._last_transition_at = started_iso
        self._effective_mode = self._initial_effective_mode()
        self._last_blockers = tuple(self._compute_blockers())
        self._append_audit(
            "rollout_initialized",
            f"inference rollout initialized in {self._effective_mode} mode",
            {
                "configured_mode": self._configured_mode,
                "target_mode": self._target_mode,
                "effective_mode": self._effective_mode,
                "force_primary": self._force_primary,
                "model_id": self._active_model.model_id if self._active_model is not None else None,
            },
            created_at=started_iso,
        )
        if self._configured_mode == "primary" and self._effective_mode != "primary":
            self._append_audit(
                "rollout_holdback",
                "primary rollout held back until promotion gates pass",
                {"blockers": list(self._last_blockers)},
                created_at=started_iso,
            )

    async def restore(self) -> None:
        if self._state_store is None:
            return
        try:
            payload = await self._state_store.load_state()
        except Exception as exc:
            self._record_state_error("load", exc)
            return
        if payload is None:
            return
        reason = self._restore_state(payload)
        if reason is None:
            self._state_restored = True
            self._append_audit(
                "rollout_resumed",
                "inference rollout state restored from persistent storage",
                {
                    "observed_ticks": self._observed_ticks,
                    "compared_ticks": self._compared_ticks,
                    "backend": self._state_store.backend_name,
                },
            )
            await self._persist_state(force=True)
            return
        self._append_audit(
            "rollout_restore_skipped",
            "inference rollout state restore skipped",
            {"reason": reason, "backend": self._state_store.backend_name},
        )

    def effective_mode(self) -> str:
        return self._effective_mode

    async def record_observation(
        self,
        *,
        symbol: str,
        rule_signal: str,
        inference_decision: InferenceDecision | None,
    ) -> None:
        self._observed_ticks += 1
        if inference_decision is None:
            self._dirty_observations += 1
            if self._dirty_observations >= self._persist_every_observations:
                await self._persist_state(force=False)
            return

        self._compared_ticks += 1
        self._rule_signal_counts[rule_signal] += 1
        self._inference_signal_counts[inference_decision.signal] += 1
        symbol_counter = self._symbol_counters.setdefault(symbol, _SymbolCounter())
        symbol_counter.compared_ticks += 1
        if rule_signal == inference_decision.signal:
            self._agreement_count += 1
            symbol_counter.agreement_count += 1
        else:
            self._divergence_count += 1
            symbol_counter.divergence_count += 1

        should_persist = self._maybe_emit_comparison_milestone()
        current_blockers = tuple(self._compute_blockers())
        if current_blockers != self._last_blockers:
            self._append_audit(
                "rollout_blockers_changed",
                "inference rollout blockers changed",
                {
                    "previous_blockers": list(self._last_blockers),
                    "current_blockers": list(current_blockers),
                    "compared_ticks": self._compared_ticks,
                    "agreement_ratio": self._agreement_ratio(),
                },
            )
            self._last_blockers = current_blockers
            should_persist = True

        previous_mode = self._effective_mode
        next_mode = self._resolve_effective_mode(current_blockers=current_blockers)
        if previous_mode != next_mode:
            self._effective_mode = next_mode
            transition_time = _utc_now_iso()
            self._last_transition_at = transition_time
            self._append_audit(
                "rollout_transition",
                f"inference rollout transitioned from {previous_mode} to {next_mode}",
                {
                    "from": previous_mode,
                    "to": next_mode,
                    "compared_ticks": self._compared_ticks,
                    "agreement_ratio": self._agreement_ratio(),
                },
                created_at=transition_time,
            )
            should_persist = True

        self._dirty_observations += 1
        if should_persist or self._dirty_observations >= self._persist_every_observations:
            await self._persist_state(force=should_persist)

    def snapshot(self) -> InferenceRolloutSnapshot:
        blockers = self._compute_blockers()
        return InferenceRolloutSnapshot(
            configured_mode=self._configured_mode,
            target_mode=self._target_mode,
            effective_mode=self._effective_mode,
            override_active=self._target_mode != self._configured_mode,
            auto_promote_enabled=self._target_mode == "primary" and not self._force_primary,
            force_primary=self._force_primary,
            promotion_eligible=not blockers if self._target_mode == "primary" else False,
            state_backend=self._state_store.backend_name if self._state_store is not None else None,
            state_restored=self._state_restored,
            last_persisted_at=self._last_persisted_at,
            blockers=tuple(blockers),
            required_observe_ticks=self._required_observe_ticks,
            compared_ticks=self._compared_ticks,
            required_agreement_ratio=self._required_agreement_ratio,
            agreement_ratio=self._agreement_ratio(),
            required_macro_f1=self._required_macro_f1,
            current_macro_f1=self._current_macro_f1(),
            started_at=self._started_at,
            last_transition_at=self._last_transition_at,
        )

    def comparison(self) -> InferenceComparisonSnapshot:
        symbol_snapshots = tuple(
            counter.to_snapshot(symbol=symbol)
            for symbol, counter in sorted(
                self._symbol_counters.items(),
                key=lambda item: (-item[1].compared_ticks, item[0]),
            )
        )
        return InferenceComparisonSnapshot(
            observed_ticks=self._observed_ticks,
            compared_ticks=self._compared_ticks,
            agreement_count=self._agreement_count,
            divergence_count=self._divergence_count,
            rule_signal_counts=dict(self._rule_signal_counts),
            inference_signal_counts=dict(self._inference_signal_counts),
            symbols=symbol_snapshots,
        )

    def recent_audit_events(self, *, limit: int = 10) -> tuple[InferenceAuditEvent, ...]:
        if limit <= 0:
            return ()
        return tuple(list(self._audit_events)[-limit:])

    async def flush(self) -> None:
        await self._persist_state(force=True)

    async def set_target_mode(
        self,
        *,
        target_mode: str,
        actor: str | None = None,
        reason: str | None = None,
        request_id: str | None = None,
    ) -> None:
        normalized_target = target_mode.strip().lower()
        if normalized_target not in {"observe", "primary", "disabled"}:
            raise ValueError("target_mode must be one of: disabled, observe, primary")
        if self._configured_mode == "disabled":
            normalized_target = "disabled"

        previous_target = self._target_mode
        previous_mode = self._effective_mode
        if previous_target == normalized_target:
            self._append_audit(
                "rollout_target_noop",
                f"inference rollout target already {normalized_target}",
                {
                    "actor": actor,
                    "reason": reason,
                    "target_mode": normalized_target,
                },
                request_id=request_id,
            )
            await self._persist_state(force=True)
            return

        self._target_mode = normalized_target
        self._last_blockers = tuple(self._compute_blockers())
        next_mode = self._resolve_effective_mode(current_blockers=self._last_blockers)
        self._append_audit(
            "rollout_target_changed",
            f"inference rollout target changed from {previous_target} to {normalized_target}",
            {
                "actor": actor,
                "reason": reason,
                "from_target_mode": previous_target,
                "to_target_mode": normalized_target,
                "override_active": normalized_target != self._configured_mode,
            },
            request_id=request_id,
        )
        if previous_mode != next_mode:
            self._effective_mode = next_mode
            self._last_transition_at = _utc_now_iso()
            self._append_audit(
                "rollout_transition",
                f"inference rollout transitioned from {previous_mode} to {next_mode}",
                {
                    "actor": actor,
                    "reason": reason,
                    "from": previous_mode,
                    "to": next_mode,
                    "compared_ticks": self._compared_ticks,
                    "agreement_ratio": self._agreement_ratio(),
                },
                created_at=self._last_transition_at,
                request_id=request_id,
            )
        elif normalized_target == "primary" and self._last_blockers:
            self._append_audit(
                "rollout_holdback",
                "primary rollout held back until promotion gates pass",
                {
                    "actor": actor,
                    "reason": reason,
                    "blockers": list(self._last_blockers),
                },
                request_id=request_id,
            )
        await self._persist_state(force=True)

    async def set_active_model(
        self,
        *,
        model: RegisteredModel | None,
        actor: str | None = None,
        reason: str | None = None,
        request_id: str | None = None,
    ) -> None:
        previous_model = self._active_model
        previous_key = _model_key(previous_model)
        next_key = _model_key(model)
        if previous_key == next_key:
            self._append_audit(
                "model_activation_noop",
                "active inference model already selected",
                {
                    "actor": actor,
                    "reason": reason,
                    "model_id": model.model_id if model is not None else None,
                    "version": model.version if model is not None else None,
                },
                request_id=request_id,
            )
            await self._persist_state(force=True)
            return

        previous_mode = self._effective_mode
        self._active_model = model
        self._observed_ticks = 0
        self._compared_ticks = 0
        self._agreement_count = 0
        self._divergence_count = 0
        self._rule_signal_counts.clear()
        self._inference_signal_counts.clear()
        self._symbol_counters.clear()
        self._emitted_milestones.clear()
        self._dirty_observations = 0
        self._last_blockers = tuple(self._compute_blockers())
        self._effective_mode = self._resolve_effective_mode(current_blockers=self._last_blockers)
        self._last_transition_at = _utc_now_iso()
        self._append_audit(
            "active_model_changed",
            "active inference model changed and rollout comparison counters reset",
            {
                "actor": actor,
                "reason": reason,
                "previous_model_id": previous_model.model_id if previous_model is not None else None,
                "previous_version": previous_model.version if previous_model is not None else None,
                "model_id": model.model_id if model is not None else None,
                "version": model.version if model is not None else None,
            },
            created_at=self._last_transition_at,
            request_id=request_id,
        )
        if previous_mode != self._effective_mode:
            self._append_audit(
                "rollout_transition",
                f"inference rollout transitioned from {previous_mode} to {self._effective_mode}",
                {
                    "actor": actor,
                    "reason": reason,
                    "from": previous_mode,
                    "to": self._effective_mode,
                    "reason_code": "active_model_changed",
                },
                created_at=self._last_transition_at,
                request_id=request_id,
            )
        await self._persist_state(force=True)

    def _initial_effective_mode(self) -> str:
        if self._configured_mode == "disabled":
            return "disabled"
        return self._resolve_effective_mode(current_blockers=tuple(self._compute_blockers()))

    def _resolve_effective_mode(self, *, current_blockers: tuple[str, ...] | None = None) -> str:
        if self._target_mode == "disabled" or self._configured_mode == "disabled":
            return "disabled"
        if self._target_mode == "observe":
            return "observe"
        if self._force_primary:
            return "primary"
        blockers = current_blockers if current_blockers is not None else tuple(self._compute_blockers())
        return "primary" if not blockers else "observe"

    def _compute_blockers(self) -> list[str]:
        if self._target_mode != "primary":
            return []
        blockers: list[str] = []
        if self._active_model is None:
            blockers.append("no_active_model")
            return blockers
        current_macro_f1 = self._current_macro_f1()
        if current_macro_f1 is None:
            blockers.append("macro_f1_missing")
        elif current_macro_f1 < self._required_macro_f1:
            blockers.append("offline_macro_f1_below_threshold")
        if self._compared_ticks < self._required_observe_ticks:
            blockers.append("insufficient_observe_ticks")
        agreement_ratio = self._agreement_ratio()
        if agreement_ratio is None:
            blockers.append("agreement_ratio_unavailable")
        elif agreement_ratio < self._required_agreement_ratio:
            blockers.append("agreement_ratio_below_threshold")
        return blockers

    def _current_macro_f1(self) -> float | None:
        if self._active_model is None:
            return None
        value = self._active_model.metadata.get("best_macro_f1")
        if isinstance(value, (int, float)):
            return float(value)
        return None

    def _agreement_ratio(self) -> float | None:
        if self._compared_ticks <= 0:
            return None
        return self._agreement_count / self._compared_ticks

    def _maybe_emit_comparison_milestone(self) -> bool:
        if self._compared_ticks <= 0:
            return False
        milestone = _comparison_milestone(self._compared_ticks)
        if milestone is None or milestone in self._emitted_milestones:
            return False
        self._emitted_milestones.add(milestone)
        self._append_audit(
            "comparison_milestone",
            f"inference comparison reached {milestone} compared ticks",
            {
                "milestone": milestone,
                "compared_ticks": self._compared_ticks,
                "agreement_ratio": self._agreement_ratio(),
                "divergence_count": self._divergence_count,
            },
        )
        return True

    def _append_audit(
        self,
        event_type: str,
        message: str,
        metadata: dict[str, object | None],
        *,
        created_at: str | None = None,
        request_id: str | None = None,
    ) -> None:
        sanitized = {key: value for key, value in metadata.items() if value is not None}
        self._audit_events.append(
            InferenceAuditEvent(
                event_type=event_type,
                created_at=created_at or _utc_now_iso(),
                message=message,
                metadata=sanitized,
                request_id=request_id,
            )
        )

    async def _persist_state(self, *, force: bool) -> None:
        if self._state_store is None:
            self._dirty_observations = 0
            return
        if not force and self._dirty_observations <= 0:
            return
        persisted_at = _utc_now_iso()
        try:
            await self._state_store.save_state(self._serialize_state(last_persisted_at=persisted_at))
        except Exception as exc:
            self._record_state_error("save", exc)
            return
        self._last_persisted_at = persisted_at
        self._dirty_observations = 0
        self._last_state_error = None

    def _serialize_state(self, *, last_persisted_at: str | None = None) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "configured_mode": self._configured_mode,
            "target_mode": self._target_mode,
            "force_primary": self._force_primary,
            "active_model": {
                "model_id": self._active_model.model_id if self._active_model is not None else None,
                "version": self._active_model.version if self._active_model is not None else None,
            },
            "started_at": self._started_at,
            "last_transition_at": self._last_transition_at,
            "effective_mode": self._effective_mode,
            "last_blockers": list(self._last_blockers),
            "observed_ticks": self._observed_ticks,
            "compared_ticks": self._compared_ticks,
            "agreement_count": self._agreement_count,
            "divergence_count": self._divergence_count,
            "rule_signal_counts": dict(self._rule_signal_counts),
            "inference_signal_counts": dict(self._inference_signal_counts),
            "symbol_counters": {
                symbol: {
                    "compared_ticks": counter.compared_ticks,
                    "agreement_count": counter.agreement_count,
                    "divergence_count": counter.divergence_count,
                }
                for symbol, counter in self._symbol_counters.items()
            },
            "emitted_milestones": sorted(self._emitted_milestones),
            "audit_events": [event.to_dict() for event in self._audit_events],
            "last_persisted_at": last_persisted_at or self._last_persisted_at,
        }

    def _restore_state(self, payload: dict[str, Any]) -> str | None:
        if int(payload.get("schema_version", 0)) != 1:
            return "schema_version_mismatch"
        if str(payload.get("configured_mode", "")) != self._configured_mode:
            return "configured_mode_mismatch"

        persisted_model = payload.get("active_model")
        if self._active_model is None:
            if persisted_model:
                return "active_model_mismatch"
        else:
            if not isinstance(persisted_model, dict):
                return "active_model_missing"
            if str(persisted_model.get("model_id", "")) != self._active_model.model_id:
                return "active_model_id_mismatch"
            if str(persisted_model.get("version", "")) != self._active_model.version:
                return "active_model_version_mismatch"

        self._started_at = str(payload.get("started_at", self._started_at))
        self._last_transition_at = str(payload.get("last_transition_at", self._last_transition_at))
        restored_target_mode = str(payload.get("target_mode", self._configured_mode)).lower()
        if restored_target_mode not in {"observe", "primary", "disabled"}:
            return "target_mode_invalid"
        self._target_mode = restored_target_mode
        restored_effective_mode = str(payload.get("effective_mode", self._effective_mode))
        self._observed_ticks = max(int(payload.get("observed_ticks", 0)), 0)
        self._compared_ticks = max(int(payload.get("compared_ticks", 0)), 0)
        self._agreement_count = max(int(payload.get("agreement_count", 0)), 0)
        self._divergence_count = max(int(payload.get("divergence_count", 0)), 0)
        self._rule_signal_counts = Counter(
            {
                str(signal): max(int(count), 0)
                for signal, count in dict(payload.get("rule_signal_counts", {})).items()
            }
        )
        self._inference_signal_counts = Counter(
            {
                str(signal): max(int(count), 0)
                for signal, count in dict(payload.get("inference_signal_counts", {})).items()
            }
        )
        self._symbol_counters = {}
        for symbol, raw_counter in dict(payload.get("symbol_counters", {})).items():
            counter_payload = dict(raw_counter)
            self._symbol_counters[str(symbol)] = _SymbolCounter(
                compared_ticks=max(int(counter_payload.get("compared_ticks", 0)), 0),
                agreement_count=max(int(counter_payload.get("agreement_count", 0)), 0),
                divergence_count=max(int(counter_payload.get("divergence_count", 0)), 0),
            )
        self._emitted_milestones = {
            max(int(milestone), 0) for milestone in payload.get("emitted_milestones", [])
        }
        self._audit_events.clear()
        for item in payload.get("audit_events", []):
            event_payload = dict(item)
            self._audit_events.append(
                InferenceAuditEvent(
                    event_type=str(event_payload.get("event_type", "unknown")),
                    created_at=str(event_payload.get("created_at", self._started_at)),
                    message=str(event_payload.get("message", "")),
                    metadata=dict(event_payload.get("metadata", {})),
                    request_id=(
                        str(event_payload.get("request_id"))
                        if isinstance(event_payload.get("request_id"), str)
                        and str(event_payload.get("request_id")).strip()
                        else None
                    ),
                )
            )
        current_blockers = tuple(self._compute_blockers())
        self._last_blockers = current_blockers
        self._effective_mode = self._resolve_effective_mode(current_blockers=current_blockers)
        if restored_effective_mode != self._effective_mode:
            self._last_transition_at = _utc_now_iso()
            self._append_audit(
                "rollout_transition",
                f"inference rollout transitioned from {restored_effective_mode} to {self._effective_mode}",
                {
                    "from": restored_effective_mode,
                    "to": self._effective_mode,
                    "reason": "recomputed from persisted comparison state",
                },
                created_at=self._last_transition_at,
            )
        self._last_persisted_at = str(payload.get("last_persisted_at", ""))
        self._dirty_observations = 0
        return None

    def _record_state_error(self, action: str, exc: Exception) -> None:
        message = f"{action}: {exc}"
        if message == self._last_state_error:
            return
        self._last_state_error = message
        self._append_audit(
            "rollout_state_degraded",
            "persistent rollout state backend unavailable",
            {
                "backend": self._state_store.backend_name if self._state_store is not None else None,
                "action": action,
                "error": str(exc),
            },
        )


def _iso_from_timestamp(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, tz=UTC).isoformat().replace("+00:00", "Z")


def _utc_now_iso() -> str:
    return datetime.now(tz=UTC).isoformat().replace("+00:00", "Z")


def _comparison_milestone(compared_ticks: int) -> int | None:
    milestones = (10, 25, 50, 100, 250, 500, 1000)
    for milestone in milestones:
        if compared_ticks == milestone:
            return milestone
    if compared_ticks > milestones[-1] and compared_ticks % 1000 == 0:
        return compared_ticks
    return None


def _model_key(model: RegisteredModel | None) -> str | None:
    if model is None:
        return None
    return f"{model.model_id}:{model.version}"
