from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass
from datetime import UTC, datetime

from app.ports import (
    InferenceAuditEvent,
    InferenceComparisonSnapshot,
    InferenceDecision,
    InferenceRolloutSnapshot,
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
    ) -> None:
        self._configured_mode = configured_mode
        self._active_model = active_model
        self._required_macro_f1 = required_macro_f1
        self._required_observe_ticks = required_observe_ticks
        self._required_agreement_ratio = required_agreement_ratio
        self._force_primary = force_primary
        self._observed_ticks = 0
        self._compared_ticks = 0
        self._agreement_count = 0
        self._divergence_count = 0
        self._rule_signal_counts: Counter[str] = Counter()
        self._inference_signal_counts: Counter[str] = Counter()
        self._symbol_counters: dict[str, _SymbolCounter] = {}
        self._audit_events: deque[InferenceAuditEvent] = deque(maxlen=max_audit_events)
        self._emitted_milestones: set[int] = set()
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

    def effective_mode(self) -> str:
        return self._effective_mode

    def record_observation(
        self,
        *,
        symbol: str,
        rule_signal: str,
        inference_decision: InferenceDecision | None,
    ) -> None:
        self._observed_ticks += 1
        if inference_decision is None:
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

        self._maybe_emit_comparison_milestone()
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

    def snapshot(self) -> InferenceRolloutSnapshot:
        blockers = self._compute_blockers()
        return InferenceRolloutSnapshot(
            configured_mode=self._configured_mode,
            effective_mode=self._effective_mode,
            auto_promote_enabled=self._configured_mode == "primary" and not self._force_primary,
            force_primary=self._force_primary,
            promotion_eligible=not blockers if self._configured_mode == "primary" else False,
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

    def _initial_effective_mode(self) -> str:
        if self._configured_mode == "disabled":
            return "disabled"
        return self._resolve_effective_mode(current_blockers=tuple(self._compute_blockers()))

    def _resolve_effective_mode(self, *, current_blockers: tuple[str, ...] | None = None) -> str:
        if self._configured_mode == "disabled":
            return "disabled"
        if self._configured_mode == "observe":
            return "observe"
        if self._force_primary:
            return "primary"
        blockers = current_blockers if current_blockers is not None else tuple(self._compute_blockers())
        return "primary" if not blockers else "observe"

    def _compute_blockers(self) -> list[str]:
        if self._configured_mode != "primary":
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

    def _maybe_emit_comparison_milestone(self) -> None:
        if self._compared_ticks <= 0:
            return
        milestone = _comparison_milestone(self._compared_ticks)
        if milestone is None or milestone in self._emitted_milestones:
            return
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

    def _append_audit(
        self,
        event_type: str,
        message: str,
        metadata: dict[str, object | None],
        *,
        created_at: str | None = None,
    ) -> None:
        sanitized = {key: value for key, value in metadata.items() if value is not None}
        self._audit_events.append(
            InferenceAuditEvent(
                event_type=event_type,
                created_at=created_at or _utc_now_iso(),
                message=message,
                metadata=sanitized,
            )
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
