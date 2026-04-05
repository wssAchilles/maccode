"""Compute rollout policy view enriched with runtime readiness."""

from __future__ import annotations

from typing import Any, Dict, List

from services.compute_benchmark_gate_service import ComputeBenchmarkGateService
from services.compute_rollout_guard_service import ComputeRolloutGuardService
from services.compute_rollout_service import ComputeRolloutService
from services.compute_runtime_probe_service import ComputeRuntimeProbeService


class ComputeGovernanceStatusService:
    """Build dashboard-facing rollout policy with live runtime diagnostics."""

    @classmethod
    def get_policy_view(cls, policy: Dict[str, Any] | None = None) -> Dict[str, Any]:
        serialized = ComputeRolloutService.serialize_policy(policy)
        runtime_targets = ComputeRuntimeProbeService.get_runtime_targets()
        guard_state = ComputeRolloutGuardService.get_state()
        components = []
        for component in serialized.get('components', []):
            if not isinstance(component, dict):
                continue
            components.append(
                cls._enrich_component(
                    component,
                    runtime_targets,
                    guard_state=guard_state,
                ),
            )

        return {
            **serialized,
            'runtime_targets': runtime_targets,
            'guard_enabled': bool(guard_state.get('guard_enabled')),
            'guard_failure_threshold': int(guard_state.get('failure_threshold') or 3),
            'guard_window_minutes': int(guard_state.get('window_minutes') or 30),
            'components': components,
        }

    @classmethod
    def _enrich_component(
        cls,
        component: Dict[str, Any],
        runtime_targets: List[Dict[str, Any]],
        *,
        guard_state: Dict[str, Any],
    ) -> Dict[str, Any]:
        component_key = str(component.get('key') or '')
        rollout_mode = str(component.get('rollout_mode') or '')
        canary_percent = int(component.get('canary_percent') or 0)
        benchmark_gate = ComputeBenchmarkGateService.summarize_policy(component)
        benchmark_ready = bool(benchmark_gate.get('benchmark_ready'))
        require_benchmark = bool(component.get('require_benchmark'))
        component_guard = (
            dict(guard_state.get('components', {}).get(component_key) or {})
            if isinstance(guard_state.get('components'), dict)
            else {}
        )

        relevant_targets = cls._relevant_targets(component_key, runtime_targets)
        native_ready_targets = [
            target.get('worker_key')
            for target in relevant_targets
            if bool(target.get('native_enabled')) and bool(target.get('native_available'))
        ]

        rollout_status = 'stable'
        rollout_blocker = ''
        if component_key == 'feature_engineering' and rollout_mode in {
            'native_candidate',
            'native_enforced',
        }:
            if rollout_mode == 'native_candidate' and canary_percent <= 0:
                rollout_status = 'blocked'
                rollout_blocker = 'Native 灰度比例为 0%，当前不会命中任何 Native 流量'
            elif require_benchmark and not benchmark_ready:
                benchmark_status = str(benchmark_gate.get('benchmark_status') or '')
                rollout_status = {
                    'stale': 'benchmark_stale',
                    'failed': 'benchmark_failed',
                    'recorded': 'benchmark_recorded',
                }.get(benchmark_status, 'benchmark_pending')
                rollout_blocker = str(
                    benchmark_gate.get('benchmark_summary')
                    or 'Native rollout 仍缺少 benchmark 准入结果',
                )
            elif not native_ready_targets:
                rollout_status = 'blocked'
                rollout_blocker = '没有可用的 native-capable worker，当前会回退到 Python'
            elif rollout_mode == 'native_enforced':
                rollout_status = 'native_enforced'
            else:
                rollout_status = 'canary_ready'
        elif (
            component_key == 'feature_engineering'
            and rollout_mode == 'python_stable'
            and str(component_guard.get('last_auto_rollback_at') or '').strip()
        ):
            rollout_status = 'auto_rolled_back'
        elif component_key == 'scenario_simulation':
            rollout_status = (
                'vectorized_active' if rollout_mode == 'vectorized_python' else 'loop_pinned'
            )

        return {
            **component,
            'runtime_targets': relevant_targets,
            'native_ready_targets': native_ready_targets,
            'rollout_status': rollout_status,
            'rollout_blocker': rollout_blocker,
            **benchmark_gate,
            'guard_enabled': bool(guard_state.get('guard_enabled')),
            'guard_failure_threshold': int(guard_state.get('failure_threshold') or 3),
            'guard_window_minutes': int(guard_state.get('window_minutes') or 30),
            'recent_failure_count': int(component_guard.get('recent_failure_count') or 0),
            'last_failure_at': str(component_guard.get('last_failure_at') or ''),
            'last_failure_reason': str(component_guard.get('last_failure_reason') or ''),
            'last_failure_context': str(component_guard.get('last_failure_context') or ''),
            'last_success_at': str(component_guard.get('last_success_at') or ''),
            'auto_rollback_count': int(component_guard.get('auto_rollback_count') or 0),
            'last_auto_rollback_at': str(component_guard.get('last_auto_rollback_at') or ''),
            'last_auto_rollback_reason': str(
                component_guard.get('last_auto_rollback_reason') or '',
            ),
            'last_auto_rollback_to': str(component_guard.get('last_auto_rollback_to') or ''),
        }

    @staticmethod
    def _relevant_targets(
        component_key: str,
        runtime_targets: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        targets = [
            dict(target)
            for target in runtime_targets
            if isinstance(target, dict)
        ]
        if component_key == 'scenario_simulation':
            return [
                target
                for target in targets
                if str(target.get('worker_key') or '') == 'light_worker'
            ] or targets[:1]
        return targets
