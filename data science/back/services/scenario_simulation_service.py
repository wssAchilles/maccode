"""Structured scenario simulation orchestration."""

from __future__ import annotations

from time import perf_counter
from typing import Any, Dict, List, Sequence, Tuple

from services.compute_acceleration_service import ComputeAccelerationService
from services.compute_backend_selector import select_scenario_simulation_backend
from services.scenario_kernels import (
    expand_variations,
    simulate_scenarios_loop,
    simulate_scenarios_vectorized,
)


class ScenarioSimulationService:
    """Run scenario simulation without bloating the main optimization service."""

    @staticmethod
    def simulate(
        *,
        load_profile: Sequence[float],
        price_profile: Sequence[float],
        variations: Dict[str, List[Any]] | None,
        battery_capacity: float,
        max_power: float,
        efficiency: float,
        initial_soc: float = 0.5,
        context: str = 'scenario_simulation',
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        started_at = perf_counter()
        param_names, scenario_params = expand_variations(
            variations,
            base_battery_capacity=battery_capacity,
            base_max_power=max_power,
        )
        selection = select_scenario_simulation_backend(context=context)

        if selection['backend'] == 'python_vectorized':
            results = simulate_scenarios_vectorized(
                load_profile=load_profile,
                price_profile=price_profile,
                scenario_params=scenario_params,
                base_battery_capacity=battery_capacity,
                base_max_power=max_power,
                efficiency=efficiency,
                initial_soc=initial_soc,
            )
        else:
            results = simulate_scenarios_loop(
                load_profile=load_profile,
                price_profile=price_profile,
                scenario_params=scenario_params,
                base_battery_capacity=battery_capacity,
                base_max_power=max_power,
                efficiency=efficiency,
                initial_soc=initial_soc,
            )

        duration_ms = (perf_counter() - started_at) * 1000.0
        metrics = {
            'backend': selection['backend'],
            'rollout_mode': selection['rollout_mode'],
            'rollout_reason': selection['rollout_reason'],
            'preferred_backend': selection['preferred_backend'],
            'duration_ms': round(duration_ms, 3),
            'input_rows': len(results),
            'scenario_count': len(results),
            'load_points': len(load_profile),
            'price_points': len(price_profile),
            'variation_keys': param_names,
            'context': context,
        }

        ComputeAccelerationService.record_component_sample(
            component='scenario_simulation',
            duration_ms=duration_ms,
            rows=len(results),
            backend=selection['backend'],
            context=context,
            native_enabled=False,
            native_available=False,
            preferred_backend=selection['preferred_backend'],
            metadata={
                'load_points': len(load_profile),
                'price_points': len(price_profile),
                'scenario_count': len(results),
                'variation_keys': param_names,
                'rollout_mode': selection['rollout_mode'],
                'rollout_reason': selection['rollout_reason'],
            },
        )

        return results, metrics
