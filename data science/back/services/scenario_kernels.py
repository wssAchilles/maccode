"""Scenario simulation kernels kept separate from the optimization service."""

from __future__ import annotations

from itertools import product
from typing import Any, Dict, List, Sequence, Tuple

import numpy as np


def expand_variations(
    variations: Dict[str, List[Any]] | None,
    *,
    base_battery_capacity: float,
    base_max_power: float,
) -> Tuple[List[str], List[Dict[str, Any]]]:
    if not variations:
        variations = {
            'battery_capacity': [
                base_battery_capacity * 0.5,
                base_battery_capacity,
                base_battery_capacity * 1.5,
            ],
            'max_power': [
                base_max_power * 0.5,
                base_max_power,
                base_max_power * 1.5,
            ],
        }

    param_names = list(variations.keys())
    param_values = list(variations.values())
    combinations = [
        dict(zip(param_names, combo))
        for combo in product(*param_values)
    ]
    return param_names, combinations


def _simulate_single_greedy(
    *,
    load: np.ndarray,
    price: np.ndarray,
    battery_capacity: float,
    max_power: float,
    efficiency: float,
    initial_soc: float,
) -> Dict[str, Any]:
    energy = float(initial_soc) * float(battery_capacity)
    reserve_high = float(battery_capacity) * 0.9
    reserve_low = float(battery_capacity) * 0.1

    schedule: List[Dict[str, Any]] = []
    total_cost = 0.0

    for hour in range(len(load)):
        p_charge = 0.0
        p_discharge = 0.0

        if price[hour] <= 0.4 and energy < reserve_high:
            p_charge = min(
                float(max_power),
                max((reserve_high - energy) / float(efficiency), 0.0),
            )
            energy += p_charge * float(efficiency)
        elif price[hour] >= 0.8 and energy > reserve_low:
            p_discharge = min(
                float(max_power),
                float(load[hour]),
                max((energy - reserve_low) * float(efficiency), 0.0),
            )
            energy -= p_discharge / float(efficiency)

        grid_power = float(load[hour]) + p_charge - p_discharge
        total_cost += grid_power * float(price[hour])
        soc = energy / float(battery_capacity) if battery_capacity else 0.0

        schedule.append(
            {
                'hour': hour,
                'load': float(load[hour]),
                'price': float(price[hour]),
                'charge_power': float(p_charge),
                'discharge_power': float(p_discharge),
                'battery_action': float(p_charge - p_discharge),
                'soc': float(soc),
                'stored_energy': float(energy),
                'grid_power': float(grid_power),
            }
        )

    cost_without_battery = float(np.sum(load * price))
    savings = cost_without_battery - total_cost
    savings_percent = (savings / cost_without_battery * 100.0) if cost_without_battery > 0 else 0.0
    return {
        'status': 'Greedy_Fallback',
        'schedule': schedule,
        'total_cost_without_battery': float(cost_without_battery),
        'total_cost_with_battery': float(total_cost),
        'savings': float(savings),
        'savings_percent': float(savings_percent),
        'algorithm': 'greedy',
    }


def simulate_scenarios_loop(
    *,
    load_profile: Sequence[float],
    price_profile: Sequence[float],
    scenario_params: Sequence[Dict[str, Any]],
    base_battery_capacity: float,
    base_max_power: float,
    efficiency: float,
    initial_soc: float,
) -> List[Dict[str, Any]]:
    load = np.asarray(load_profile, dtype=float)
    price = np.asarray(price_profile, dtype=float)
    results: List[Dict[str, Any]] = []
    for params in scenario_params:
        battery_capacity = float(params.get('battery_capacity', base_battery_capacity))
        max_power = float(params.get('max_power', base_max_power))
        result = _simulate_single_greedy(
            load=load,
            price=price,
            battery_capacity=battery_capacity,
            max_power=max_power,
            efficiency=efficiency,
            initial_soc=initial_soc,
        )
        result['params'] = dict(params)
        result['backend'] = 'python_loop'
        results.append(result)
    results.sort(key=lambda item: item.get('savings', 0), reverse=True)
    return results


def simulate_scenarios_vectorized(
    *,
    load_profile: Sequence[float],
    price_profile: Sequence[float],
    scenario_params: Sequence[Dict[str, Any]],
    base_battery_capacity: float,
    base_max_power: float,
    efficiency: float,
    initial_soc: float,
) -> List[Dict[str, Any]]:
    load = np.asarray(load_profile, dtype=float)
    price = np.asarray(price_profile, dtype=float)
    scenario_count = len(scenario_params)
    if scenario_count == 0:
        return []

    capacities = np.asarray(
        [float(params.get('battery_capacity', base_battery_capacity)) for params in scenario_params],
        dtype=float,
    )
    powers = np.asarray(
        [float(params.get('max_power', base_max_power)) for params in scenario_params],
        dtype=float,
    )

    energy = capacities * float(initial_soc)
    reserve_high = capacities * 0.9
    reserve_low = capacities * 0.1

    charge = np.zeros((scenario_count, len(load)), dtype=float)
    discharge = np.zeros((scenario_count, len(load)), dtype=float)
    energy_history = np.zeros((scenario_count, len(load)), dtype=float)
    soc_history = np.zeros((scenario_count, len(load)), dtype=float)
    grid_power = np.zeros((scenario_count, len(load)), dtype=float)

    for hour in range(len(load)):
        can_charge = (price[hour] <= 0.4) & (energy < reserve_high)
        max_charge = np.minimum(
            powers,
            np.maximum((reserve_high - energy) / float(efficiency), 0.0),
        )
        step_charge = np.where(can_charge, max_charge, 0.0)
        energy_after_charge = energy + step_charge * float(efficiency)

        can_discharge = (price[hour] >= 0.8) & (energy_after_charge > reserve_low) & (~can_charge)
        max_discharge = np.minimum.reduce(
            [
                powers,
                np.full(scenario_count, float(load[hour])),
                np.maximum((energy_after_charge - reserve_low) * float(efficiency), 0.0),
            ]
        )
        step_discharge = np.where(can_discharge, max_discharge, 0.0)
        energy = energy_after_charge - step_discharge / float(efficiency)

        charge[:, hour] = step_charge
        discharge[:, hour] = step_discharge
        energy_history[:, hour] = energy
        soc_history[:, hour] = np.divide(
            energy,
            capacities,
            out=np.zeros_like(energy),
            where=capacities != 0,
        )
        grid_power[:, hour] = float(load[hour]) + step_charge - step_discharge

    total_cost_with_battery = np.sum(grid_power * price.reshape(1, -1), axis=1)
    total_cost_without_battery = float(np.sum(load * price))
    savings = total_cost_without_battery - total_cost_with_battery
    savings_percent = np.where(
        total_cost_without_battery > 0,
        savings / total_cost_without_battery * 100.0,
        0.0,
    )

    results: List[Dict[str, Any]] = []
    for index, params in enumerate(scenario_params):
        schedule = [
            {
                'hour': hour,
                'load': float(load[hour]),
                'price': float(price[hour]),
                'charge_power': float(charge[index, hour]),
                'discharge_power': float(discharge[index, hour]),
                'battery_action': float(charge[index, hour] - discharge[index, hour]),
                'soc': float(soc_history[index, hour]),
                'stored_energy': float(energy_history[index, hour]),
                'grid_power': float(grid_power[index, hour]),
            }
            for hour in range(len(load))
        ]
        results.append(
            {
                'status': 'Greedy_Vectorized',
                'schedule': schedule,
                'total_cost_without_battery': float(total_cost_without_battery),
                'total_cost_with_battery': float(total_cost_with_battery[index]),
                'savings': float(savings[index]),
                'savings_percent': float(savings_percent[index]),
                'algorithm': 'greedy_vectorized',
                'params': dict(params),
                'backend': 'python_vectorized',
            }
        )

    results.sort(key=lambda item: item.get('savings', 0), reverse=True)
    return results
