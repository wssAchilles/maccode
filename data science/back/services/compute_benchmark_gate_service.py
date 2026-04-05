"""Benchmark gate evaluation for compute rollout governance.

Keeps benchmark pass/fail semantics out of persistence and UI layers so rollout
selection can rely on a compact, explicit gate contract.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from config import Config


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    except Exception:
        return None


class ComputeBenchmarkGateService:
    """Evaluate benchmark evidence for rollout decisions."""

    @staticmethod
    def _threshold_for(component: str) -> float:
        if component == 'feature_engineering':
            return float(getattr(Config, 'COMPUTE_FEATURE_NATIVE_MIN_SPEEDUP', 1.15))
        if component == 'scenario_simulation':
            return float(getattr(Config, 'COMPUTE_SCENARIO_VECTOR_MIN_SPEEDUP', 1.05))
        return 1.0

    @staticmethod
    def _stale_hours() -> int:
        return int(getattr(Config, 'COMPUTE_BENCHMARK_STALE_HOURS', 168) or 168)

    @classmethod
    def build_policy_patch(
        cls,
        component: str,
        *,
        context: str,
        backend: str,
        baseline_duration_ms: float | None,
        candidate_duration_ms: float | None,
        sample_rows: int = 0,
        error: str = '',
    ) -> Dict[str, Any]:
        threshold = cls._threshold_for(component)
        speedup_ratio = None
        if (
            baseline_duration_ms is not None
            and candidate_duration_ms not in (None, 0)
        ):
            speedup_ratio = round(float(baseline_duration_ms) / float(candidate_duration_ms), 3)

        if error:
            status = 'failed'
            passed = False
            summary = f'Benchmark failed: {str(error).strip()[:180]}'
        elif speedup_ratio is None:
            status = 'failed'
            passed = False
            summary = 'Benchmark did not produce a valid candidate duration'
        elif speedup_ratio >= threshold:
            status = 'passed'
            passed = True
            summary = f'Benchmark passed at {speedup_ratio}x speedup'
        else:
            status = 'failed'
            passed = False
            summary = (
                f'Benchmark below threshold: {speedup_ratio}x < {threshold}x'
            )

        return {
            'last_benchmark_at': _utc_now().isoformat(),
            'last_benchmark_context': str(context or '')[:160],
            'last_benchmark_backend': str(backend or '')[:64],
            'benchmark_status': status,
            'benchmark_passed': passed,
            'benchmark_summary': summary[:240],
            'benchmark_speedup_ratio': speedup_ratio,
            'benchmark_threshold': threshold,
            'benchmark_sample_rows': int(sample_rows or 0),
        }

    @classmethod
    def build_recorded_patch(
        cls,
        component: str,
        *,
        context: str,
        backend: str,
    ) -> Dict[str, Any]:
        return {
            'last_benchmark_at': _utc_now().isoformat(),
            'last_benchmark_context': str(context or '')[:160],
            'last_benchmark_backend': str(backend or '')[:64],
            'benchmark_status': 'recorded',
            'benchmark_passed': False,
            'benchmark_summary': 'Benchmark sample recorded; rerun governed benchmark for rollout admission',
            'benchmark_speedup_ratio': None,
            'benchmark_threshold': cls._threshold_for(component),
            'benchmark_sample_rows': 0,
        }

    @classmethod
    def summarize_policy(cls, component_policy: Dict[str, Any] | None) -> Dict[str, Any]:
        payload = dict(component_policy or {})
        status = str(payload.get('benchmark_status') or '').strip() or 'pending'
        passed = bool(payload.get('benchmark_passed'))
        summary = str(payload.get('benchmark_summary') or '').strip()
        threshold = float(payload.get('benchmark_threshold') or cls._threshold_for(str(payload.get('key') or '')))
        benchmark_at = _parse_iso(payload.get('last_benchmark_at'))
        stale = False
        if benchmark_at is not None:
            stale = benchmark_at < (_utc_now() - timedelta(hours=cls._stale_hours()))
        if stale and status == 'passed':
            status = 'stale'
            passed = False
            if not summary:
                summary = 'Benchmark evidence is stale and must be refreshed'

        if status == 'pending' and not summary:
            summary = 'Benchmark not run yet'
        if status == 'recorded' and not summary:
            summary = 'Benchmark sample recorded but not admitted'
        if status == 'failed' and not summary:
            summary = f'Benchmark did not satisfy {threshold}x threshold'
        if status == 'stale' and not summary:
            summary = 'Benchmark evidence is stale and must be refreshed'

        return {
            'benchmark_status': status,
            'benchmark_passed': passed,
            'benchmark_summary': summary[:240],
            'benchmark_speedup_ratio': payload.get('benchmark_speedup_ratio'),
            'benchmark_threshold': threshold,
            'benchmark_sample_rows': int(payload.get('benchmark_sample_rows') or 0),
            'benchmark_stale': stale,
            'benchmark_ready': passed,
        }
