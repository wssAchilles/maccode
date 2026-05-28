from __future__ import annotations

import pytest
from domain.traffic_flow.models import TrafficFlowInput
from domain.traffic_flow.service import TrafficFlowService


def test_traffic_flow_identifies_free_flow() -> None:
    result = TrafficFlowService(free_flow_speed_kmh=80.0, jam_density_veh_per_km=120.0).analyze(
        TrafficFlowInput(
            vehicle_count=2,
            segment_length_m=500.0,
            mean_speed_kmh=72.0,
            observation_window_sec=60.0,
        )
    )

    assert result.density_k_veh_per_km == pytest.approx(4.0)
    assert result.flow_q_veh_per_hour == pytest.approx(120.0)
    assert result.congestion_level == "free_flow"


def test_traffic_flow_identifies_critical_and_congested_states() -> None:
    service = TrafficFlowService(free_flow_speed_kmh=80.0, jam_density_veh_per_km=120.0)

    critical = service.analyze(
        TrafficFlowInput(
            vehicle_count=30,
            segment_length_m=500.0,
            mean_speed_kmh=40.0,
            observation_window_sec=60.0,
        )
    )
    congested = service.analyze(
        TrafficFlowInput(
            vehicle_count=50,
            segment_length_m=500.0,
            mean_speed_kmh=12.0,
            observation_window_sec=60.0,
        )
    )

    assert critical.congestion_level == "critical_flow"
    assert congested.congestion_level == "congested_flow"
    assert "Greenshields" in congested.model_explanation
