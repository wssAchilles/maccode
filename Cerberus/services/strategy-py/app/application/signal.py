from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.config import settings
from app.ports import (
    InferenceDecision,
    InferenceEnginePort,
    PortfolioSignalSnapshot,
    InferenceRolloutPort,
    SignalClaimPort,
    SignalDecisionSnapshot,
    SignalEventPort,
    SignalHistorySource,
    SignalPublisherPort,
    SignalRuntimePort,
    SignalStorePort,
    SignalStoreSource,
    StrategyDecisionSnapshot,
    StrategyOrchestrationPort,
    StrategyOrchestrationSnapshot,
    StrategyRegistryEntrySnapshot,
    StrategyRegistrySnapshot,
)
from app.schemas import Signal, SignalRecord, TickEvent


@dataclass(frozen=True, slots=True)
class SignalDecisionContext:
    engine: str
    version: str = "v1"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SignalDecision:
    signal: Signal
    context: SignalDecisionContext


class SignalApplicationService:
    def __init__(
        self,
        *,
        runtime: SignalRuntimePort,
        signal_store: SignalStorePort,
        signal_claims: SignalClaimPort,
        event_flow: SignalEventPort,
        publishers: tuple[SignalPublisherPort, ...] = (),
        default_engine_name: str = "moving_average",
        inference_engine: InferenceEnginePort | None = None,
        inference_mode: str = "disabled",
        inference_rollout: InferenceRolloutPort | None = None,
        strategy_orchestration: StrategyOrchestrationPort | None = None,
    ) -> None:
        self._runtime = runtime
        self._signal_store = signal_store
        self._signal_claims = signal_claims
        self._event_flow = event_flow
        self._publishers = publishers
        self._default_engine_name = default_engine_name
        self._inference_engine = inference_engine
        self._inference_mode = inference_mode
        self._inference_rollout = inference_rollout
        self._strategy_orchestration = strategy_orchestration

    async def startup(self) -> None:
        if self._strategy_orchestration is None:
            return
        await self._strategy_orchestration.startup()

    async def shutdown(self) -> None:
        if self._strategy_orchestration is None:
            return
        await self._strategy_orchestration.shutdown()

    def current_signal(self) -> SignalDecision | None:
        snapshot = self._runtime.read_current_decision()
        if snapshot is not None:
            return self._build_decision(
                snapshot.signal,
                metadata=self._decision_metadata_from_snapshot(snapshot),
                engine=snapshot.engine,
            )

        signal = self._runtime.read_current_signal()
        if signal is None:
            return None
        return self._build_decision(signal)

    async def ingest_tick(self, tick: TickEvent) -> SignalDecision:
        rule_signal, rule_signal_id = self._runtime.evaluate_tick(tick)
        inference_decision = await self._run_inference(tick)
        await self._record_inference_observation(
            symbol=tick.symbol,
            rule_signal=rule_signal.signal,
            inference_decision=inference_decision,
        )
        effective_inference_mode = self._effective_inference_mode()
        orchestration = self._strategy_snapshot(
            symbol=tick.symbol,
            inference_decision=inference_decision,
        )
        strategies = self._strategy_snapshots(
            rule_signal=rule_signal,
            inference_decision=inference_decision,
            effective_mode=effective_inference_mode,
            orchestration=orchestration,
        )
        selected_strategy = self._resolve_selected_strategy(
            strategies=strategies,
            effective_mode=effective_inference_mode,
            conflict_policy=orchestration.conflict_policy,
        )

        final_source = selected_strategy.source if selected_strategy is not None else "rule_engine"
        signal = rule_signal
        signal_id = rule_signal_id
        engine_name = self._default_engine_name
        if selected_strategy is not None and selected_strategy.source == "inference" and inference_decision is not None:
            signal = Signal(
                strategy_id=inference_decision.strategy_id,
                symbol=tick.symbol,
                signal=inference_decision.signal,
                confidence=inference_decision.confidence,
            )
            signal_id = self._runtime.build_signal_id(tick, signal)
            engine_name = inference_decision.engine

        portfolio = self._portfolio_snapshot(
            symbol=tick.symbol,
            price=tick.price,
            event_time=tick.event_time,
            final_signal=signal.signal,
            final_source=final_source,
            strategies=strategies,
            conflict_policy=orchestration.conflict_policy,
            downgrade_policy=orchestration.downgrade_policy,
        )
        registry = self._strategy_registry_snapshot(
            symbol=tick.symbol,
            strategies=strategies,
            effective_mode=effective_inference_mode,
            inference_decision=inference_decision,
            orchestration=orchestration,
        )
        metadata = self._decision_metadata(
            tick,
            signal_id=signal_id,
            dispatch_state="accepted",
            inference_decision=inference_decision,
            inference_mode=effective_inference_mode,
            decision_source=final_source,
            strategies=strategies,
            portfolio=portfolio,
            registry=registry,
        )
        decision_snapshot = SignalDecisionSnapshot(
            signal=signal,
            engine=engine_name,
            signal_id=signal_id,
            dispatch_state="accepted",
            decision_source=final_source,
            inference_mode=effective_inference_mode,
            strategies=strategies,
            portfolio=portfolio,
            registry=registry,
            metadata=metadata,
        )

        if not await self._signal_claims.claim_signal(signal_id):
            return self._build_decision(
                signal,
                metadata=self._decision_metadata(
                    tick,
                    signal_id=signal_id,
                    dispatch_state="duplicate",
                    inference_decision=inference_decision,
                    inference_mode=effective_inference_mode,
                    decision_source=final_source,
                    strategies=strategies,
                    portfolio=portfolio,
                    registry=registry,
                ),
                engine=engine_name,
            )

        try:
            self._runtime.store_current_signal(signal)
            self._runtime.store_current_decision(decision_snapshot)
            await self._event_flow.publish_signal_flow(signal, tick, signal_id)
            for publisher in self._publishers:
                await publisher.publish_signal(signal)
        except Exception:
            await self._signal_claims.release_signal_claim(signal_id)
            raise

        self._runtime.record_tick_processed()
        return self._build_decision(
            signal,
            metadata=metadata,
            engine=engine_name,
        )

    async def recent_signals(
        self,
        *,
        limit: int,
        source: SignalHistorySource,
    ) -> tuple[SignalStoreSource, list[SignalRecord]]:
        return await self._signal_store.list_recent(limit=limit, source=source)

    def _build_decision(
        self,
        signal: Signal,
        *,
        metadata: dict[str, Any] | None = None,
        engine: str | None = None,
    ) -> SignalDecision:
        return SignalDecision(
            signal=signal,
            context=SignalDecisionContext(
                engine=engine or self._default_engine_name,
                metadata=metadata or {},
            ),
        )

    def _decision_metadata(
        self,
        tick: TickEvent,
        *,
        signal_id: str,
        dispatch_state: str,
        inference_decision: InferenceDecision | None = None,
        inference_mode: str | None = None,
        decision_source: str = "rule_engine",
        strategies: tuple[StrategyDecisionSnapshot, ...] = (),
        portfolio: PortfolioSignalSnapshot | None = None,
        registry: StrategyRegistrySnapshot | None = None,
    ) -> dict[str, Any]:
        payload = {
            "event_time": tick.event_time,
            "price": tick.price,
            "quantity": tick.quantity,
            "signal_id": signal_id,
            "dispatch_state": dispatch_state,
            "decision_source": decision_source,
            "inference_mode": inference_mode or self._effective_inference_mode(),
            "strategy_basket": [self._strategy_payload(item) for item in strategies],
        }
        if portfolio is not None:
            payload["portfolio"] = self._portfolio_payload(portfolio)
        if registry is not None:
            payload["strategy_registry"] = self._registry_payload(registry)
        if inference_decision is not None:
            payload["inference"] = {
                "engine": inference_decision.engine,
                "signal": inference_decision.signal,
                "confidence": inference_decision.confidence,
                "model_id": inference_decision.model_id,
                "model_version": inference_decision.model_version,
                "metadata": dict(inference_decision.metadata),
            }
        return payload

    async def _run_inference(self, tick: TickEvent) -> InferenceDecision | None:
        if self._inference_engine is None or self._inference_mode == "disabled":
            return None
        return await self._inference_engine.infer_signal(
            symbol=tick.symbol,
            price=tick.price,
            quantity=tick.quantity,
            event_time=tick.event_time,
        )

    def _effective_inference_mode(self) -> str:
        if self._inference_rollout is None:
            return self._inference_mode
        return self._inference_rollout.effective_mode()

    async def _record_inference_observation(
        self,
        *,
        symbol: str,
        rule_signal: str,
        inference_decision: InferenceDecision | None,
    ) -> None:
        if self._inference_rollout is None:
            return
        await self._inference_rollout.record_observation(
            symbol=symbol,
            rule_signal=rule_signal,
            inference_decision=inference_decision,
        )

    def _decision_metadata_from_snapshot(
        self,
        snapshot: SignalDecisionSnapshot,
    ) -> dict[str, Any]:
        payload = dict(snapshot.metadata)
        payload.setdefault("signal_id", snapshot.signal_id)
        payload.setdefault("dispatch_state", snapshot.dispatch_state)
        payload.setdefault("decision_source", snapshot.decision_source)
        payload.setdefault("inference_mode", snapshot.inference_mode)
        payload.setdefault(
            "strategy_basket",
            [self._strategy_payload(item) for item in snapshot.strategies],
        )
        payload.setdefault("portfolio", self._portfolio_payload(snapshot.portfolio))
        if snapshot.registry is not None:
            payload.setdefault("strategy_registry", self._registry_payload(snapshot.registry))
        return payload

    def _strategy_snapshots(
        self,
        *,
        rule_signal: Signal,
        inference_decision: InferenceDecision | None,
        effective_mode: str,
        orchestration: StrategyOrchestrationSnapshot,
    ) -> tuple[StrategyDecisionSnapshot, ...]:
        symbol = rule_signal.symbol
        provisional: list[StrategyDecisionSnapshot] = []
        for entry in orchestration.entries:
            configured_weight = entry.configured_weight(mode=effective_mode)
            if entry.source == "rule_engine":
                eligible = entry.enabled and entry.covers_symbol(symbol)
                provisional.append(
                    StrategyDecisionSnapshot(
                        strategy_id=rule_signal.strategy_id,
                        label=entry.label,
                        engine=self._default_engine_name,
                        signal=rule_signal.signal,
                        confidence=rule_signal.confidence,
                        weight=configured_weight if eligible else 0.0,
                        priority=entry.priority,
                        role=entry.role,
                        active=False,
                        source=entry.source,
                        reason=self._strategy_reason(
                            source=entry.source,
                            enabled=entry.enabled,
                            eligible=eligible,
                            effective_mode=effective_mode,
                        ),
                        metadata={
                            **dict(entry.metadata),
                            "configured_weight": configured_weight,
                            "eligible_for_symbol": eligible,
                            "state_backend": orchestration.state_backend,
                            "state_restored": orchestration.state_restored,
                        },
                    )
                )
                continue

            if inference_decision is None:
                continue

            eligible = entry.enabled and entry.covers_symbol(symbol)
            provisional.append(
                StrategyDecisionSnapshot(
                    strategy_id=inference_decision.strategy_id,
                    label=entry.label,
                    engine=inference_decision.engine,
                    signal=inference_decision.signal,
                    confidence=inference_decision.confidence,
                    weight=configured_weight if eligible else 0.0,
                    priority=entry.priority,
                    role=entry.role,
                    active=False,
                    source=entry.source,
                    reason=self._strategy_reason(
                        source=entry.source,
                        enabled=entry.enabled,
                        eligible=eligible,
                        effective_mode=effective_mode,
                    ),
                    metadata={
                        **dict(entry.metadata),
                        **dict(inference_decision.metadata),
                        "model_id": inference_decision.model_id,
                        "model_version": inference_decision.model_version,
                        "configured_weight": configured_weight,
                        "eligible_for_symbol": eligible,
                        "state_backend": orchestration.state_backend,
                        "state_restored": orchestration.state_restored,
                    },
                )
            )

        selected = self._resolve_selected_strategy(
            strategies=tuple(provisional),
            effective_mode=effective_mode,
            conflict_policy=orchestration.conflict_policy,
        )
        selected_key = (selected.strategy_id, selected.source) if selected is not None else None
        return tuple(
            StrategyDecisionSnapshot(
                strategy_id=item.strategy_id,
                label=item.label,
                engine=item.engine,
                signal=item.signal,
                confidence=item.confidence,
                weight=item.weight,
                priority=item.priority,
                role=item.role,
                active=(item.strategy_id, item.source) == selected_key,
                source=item.source,
                reason=(
                    "effective output"
                    if (item.strategy_id, item.source) == selected_key
                    else item.reason
                ),
                metadata=dict(item.metadata),
            )
            for item in provisional
        )

    def _portfolio_snapshot(
        self,
        *,
        symbol: str,
        price: float,
        event_time: str,
        final_signal: str,
        final_source: str,
        strategies: tuple[StrategyDecisionSnapshot, ...],
        conflict_policy: str,
        downgrade_policy: str,
    ) -> PortfolioSignalSnapshot:
        weighted_scores = {"BUY": 0.0, "SELL": 0.0, "HOLD": 0.0}
        for strategy in strategies:
            weighted_scores.setdefault(strategy.signal, 0.0)
            weighted_scores[strategy.signal] += strategy.weight * strategy.confidence

        ranked_strategies = sorted(
            strategies,
            key=lambda strategy: (
                weighted_scores.get(strategy.signal, 0.0),
                strategy.active,
                -strategy.priority,
            ),
            reverse=True,
        )

        dominant_signal = max(
            weighted_scores.items(),
            key=lambda item: (item[1], item[0] == final_signal),
        )[0]
        aligned_count = sum(1 for strategy in strategies if strategy.signal == dominant_signal)
        contested_count = max(len(strategies) - aligned_count, 0)
        agreement_ratio = aligned_count / len(strategies) if strategies else None
        lead_strategy = ranked_strategies[0] if ranked_strategies else None

        if dominant_signal == "BUY":
            signal_bias = "bullish"
        elif dominant_signal == "SELL":
            signal_bias = "defensive"
        elif contested_count > 0:
            signal_bias = "contested"
        else:
            signal_bias = "neutral"

        if agreement_ratio is None:
            consensus_level = "unknown"
        elif agreement_ratio >= 0.8:
            consensus_level = "high"
        elif agreement_ratio >= 0.6:
            consensus_level = "moderate"
        else:
            consensus_level = "low"

        if final_signal == "HOLD":
            execution_ready = False
            execution_gate = "hold"
            execution_gate_reason = "final signal is HOLD"
        elif (
            agreement_ratio is not None
            and agreement_ratio <= 0.5
            and conflict_policy == "review_on_conflict"
        ):
            execution_ready = False
            execution_gate = downgrade_policy
            execution_gate_reason = "strategy basket is still contested"
        else:
            execution_ready = True
            execution_gate = "ready"
            if conflict_policy == "review_on_conflict":
                execution_gate_reason = "basket supports live execution"
            elif conflict_policy == "prefer_priority":
                execution_gate_reason = "priority policy resolved the contested basket"
            else:
                execution_gate_reason = "weighted score policy resolved the contested basket"

        return PortfolioSignalSnapshot(
            symbol=symbol,
            dominant_signal=dominant_signal,
            final_signal=final_signal,
            final_source=final_source,
            signal_bias=signal_bias,
            consensus_level=consensus_level,
            execution_ready=execution_ready,
            execution_gate=execution_gate,
            execution_gate_reason=execution_gate_reason,
            lead_strategy_id=lead_strategy.strategy_id if lead_strategy is not None else None,
            lead_strategy_label=lead_strategy.label if lead_strategy is not None else None,
            aligned_count=aligned_count,
            contested_count=contested_count,
            agreement_ratio=agreement_ratio,
            weighted_score=weighted_scores.get(dominant_signal, 0.0),
            active_strategy_count=len(strategies),
            tracked_symbols=self._runtime.tracked_symbols(),
            updated_at=event_time,
            latest_price=price,
        )

    def _strategy_payload(self, strategy: StrategyDecisionSnapshot) -> dict[str, Any]:
        return {
            "strategy_id": strategy.strategy_id,
            "label": strategy.label,
            "engine": strategy.engine,
            "signal": strategy.signal,
            "confidence": strategy.confidence,
            "weight": strategy.weight,
            "priority": strategy.priority,
            "role": strategy.role,
            "active": strategy.active,
            "source": strategy.source,
            "reason": strategy.reason,
            "metadata": dict(strategy.metadata),
        }

    def _portfolio_payload(self, portfolio: PortfolioSignalSnapshot) -> dict[str, Any]:
        return {
            "symbol": portfolio.symbol,
            "dominant_signal": portfolio.dominant_signal,
            "final_signal": portfolio.final_signal,
            "final_source": portfolio.final_source,
            "signal_bias": portfolio.signal_bias,
            "consensus_level": portfolio.consensus_level,
            "execution_ready": portfolio.execution_ready,
            "execution_gate": portfolio.execution_gate,
            "execution_gate_reason": portfolio.execution_gate_reason,
            "lead_strategy_id": portfolio.lead_strategy_id,
            "lead_strategy_label": portfolio.lead_strategy_label,
            "aligned_count": portfolio.aligned_count,
            "contested_count": portfolio.contested_count,
            "agreement_ratio": portfolio.agreement_ratio,
            "weighted_score": portfolio.weighted_score,
            "active_strategy_count": portfolio.active_strategy_count,
            "tracked_symbols": list(portfolio.tracked_symbols),
            "updated_at": portfolio.updated_at,
            "latest_price": portfolio.latest_price,
        }

    def _strategy_registry_snapshot(
        self,
        *,
        symbol: str,
        strategies: tuple[StrategyDecisionSnapshot, ...],
        effective_mode: str,
        inference_decision: InferenceDecision | None,
        orchestration: StrategyOrchestrationSnapshot,
    ) -> StrategyRegistrySnapshot:
        strategy_by_source = {item.source: item for item in strategies}
        entries: list[StrategyRegistryEntrySnapshot] = []
        for entry in orchestration.entries:
            active_strategy = strategy_by_source.get(entry.source)
            effective_enabled = entry.enabled and entry.covers_symbol(symbol)
            metadata = {
                **dict(entry.metadata),
                "active_symbol": symbol,
                "configured_mode": effective_mode,
                "eligible_for_symbol": effective_enabled,
                "state_backend": orchestration.state_backend,
                "state_restored": orchestration.state_restored,
            }
            if entry.source == "inference":
                metadata.update(
                    {
                        "model_id": inference_decision.model_id if inference_decision is not None else settings.inference_model_id,
                        "model_version": (
                            inference_decision.model_version
                            if inference_decision is not None
                            else settings.inference_model_version
                        ),
                    }
                )
            entries.append(
                StrategyRegistryEntrySnapshot(
                    strategy_id=active_strategy.strategy_id if active_strategy is not None else entry.strategy_id,
                    label=entry.label,
                    engine=active_strategy.engine if active_strategy is not None else entry.engine,
                    source=entry.source,
                    role=entry.role,
                    enabled=effective_enabled,
                    priority=entry.priority,
                    configured_weight=entry.configured_weight(mode=effective_mode),
                    effective_weight=active_strategy.weight if active_strategy is not None else 0.0,
                    symbol_coverage=entry.symbol_coverage if entry.symbol_coverage else orchestration.tracked_symbols,
                    conflict_policy=orchestration.conflict_policy,
                    downgrade_policy=orchestration.downgrade_policy,
                    metadata=metadata,
                )
            )

        return StrategyRegistrySnapshot(
            symbol=symbol,
            tracked_symbols=orchestration.tracked_symbols,
            conflict_policy=orchestration.conflict_policy,
            downgrade_policy=orchestration.downgrade_policy,
            entries=tuple(entries),
        )

    def _registry_payload(self, registry: StrategyRegistrySnapshot) -> dict[str, Any]:
        return {
            "symbol": registry.symbol,
            "tracked_symbols": list(registry.tracked_symbols),
            "conflict_policy": registry.conflict_policy,
            "downgrade_policy": registry.downgrade_policy,
            "entries": [
                {
                    "strategy_id": item.strategy_id,
                    "label": item.label,
                    "engine": item.engine,
                    "source": item.source,
                    "role": item.role,
                    "enabled": item.enabled,
                    "priority": item.priority,
                    "configured_weight": item.configured_weight,
                    "effective_weight": item.effective_weight,
                    "symbol_coverage": list(item.symbol_coverage),
                    "conflict_policy": item.conflict_policy,
                    "downgrade_policy": item.downgrade_policy,
                    "metadata": dict(item.metadata),
                }
                for item in registry.entries
            ],
        }

    def _strategy_snapshot(
        self,
        *,
        symbol: str,
        inference_decision: InferenceDecision | None,
    ) -> StrategyOrchestrationSnapshot:
        tracked_symbols = self._runtime.tracked_symbols()
        inference_model_symbols: tuple[str, ...] = ()
        if inference_decision is not None:
            candidate_symbols = inference_decision.metadata.get("symbols")
            if isinstance(candidate_symbols, (list, tuple)):
                inference_model_symbols = tuple(
                    str(item).strip().upper() for item in candidate_symbols if str(item).strip()
                )
        if not inference_model_symbols:
            inference_model_symbols = tuple(
                item.strip().upper()
                for item in settings.inference_model_symbols.split(",")
                if item.strip()
            )
        if self._strategy_orchestration is None:
            from app.infrastructure.strategy_orchestration import RuntimeStrategyOrchestrationManager

            return RuntimeStrategyOrchestrationManager().snapshot(
                tracked_symbols=tracked_symbols,
                inference_runtime_enabled=self._inference_engine is not None and self._inference_mode != "disabled",
                inference_model_symbols=inference_model_symbols,
                inference_engine_name=inference_decision.engine if inference_decision is not None else None,
            )
        return self._strategy_orchestration.snapshot(
            tracked_symbols=tracked_symbols,
            inference_runtime_enabled=self._inference_engine is not None and self._inference_mode != "disabled",
            inference_model_symbols=inference_model_symbols,
            inference_engine_name=inference_decision.engine if inference_decision is not None else None,
        )

    def _resolve_selected_strategy(
        self,
        *,
        strategies: tuple[StrategyDecisionSnapshot, ...],
        effective_mode: str,
        conflict_policy: str,
    ) -> StrategyDecisionSnapshot | None:
        eligible = tuple(item for item in strategies if item.weight > 0)
        if not eligible:
            return next((item for item in strategies if item.source == "rule_engine"), None)
        if effective_mode != "primary":
            return next((item for item in eligible if item.source == "rule_engine"), eligible[0])

        distinct_signals = {item.signal for item in eligible}
        if len(eligible) == 1 or len(distinct_signals) == 1:
            return self._select_by_policy(eligible, policy="prefer_priority")
        if conflict_policy == "review_on_conflict":
            return next((item for item in eligible if item.source == "inference"), eligible[0])
        return self._select_by_policy(eligible, policy=conflict_policy)

    def _select_by_policy(
        self,
        strategies: tuple[StrategyDecisionSnapshot, ...],
        *,
        policy: str,
    ) -> StrategyDecisionSnapshot:
        if policy == "prefer_weighted_score":
            return max(
                strategies,
                key=lambda item: (
                    item.weight * item.confidence,
                    -item.priority,
                    item.source == "inference",
                ),
            )
        return min(
            strategies,
            key=lambda item: (
                item.priority,
                -(item.weight * item.confidence),
                item.source != "inference",
            ),
        )

    def _strategy_reason(
        self,
        *,
        source: str,
        enabled: bool,
        eligible: bool,
        effective_mode: str,
    ) -> str:
        if not enabled:
            return "disabled by orchestration state"
        if not eligible:
            return "symbol not covered by orchestration state"
        if source == "inference":
            return f"running in {effective_mode}"
        return "eligible baseline strategy"
