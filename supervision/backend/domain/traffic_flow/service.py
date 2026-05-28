from __future__ import annotations

from domain.traffic_flow.models import TrafficFlowInput, TrafficFlowResult


class TrafficFlowService:
    def __init__(
        self,
        free_flow_speed_kmh: float = 80.0,
        jam_density_veh_per_km: float = 120.0,
    ) -> None:
        self.free_flow_speed_kmh = free_flow_speed_kmh
        self.jam_density_veh_per_km = jam_density_veh_per_km

    def analyze(self, flow_input: TrafficFlowInput) -> TrafficFlowResult:
        if flow_input.segment_length_m <= 0:
            raise ValueError("segment_length_m must be positive")
        if flow_input.observation_window_sec <= 0:
            raise ValueError("observation_window_sec must be positive")
        if flow_input.vehicle_count < 0:
            raise ValueError("vehicle_count must not be negative")

        density = flow_input.vehicle_count / (flow_input.segment_length_m / 1000.0)
        flow = flow_input.vehicle_count / flow_input.observation_window_sec * 3600.0
        greenshields_speed = self.free_flow_speed_kmh * max(
            0.0,
            1.0 - density / self.jam_density_veh_per_km,
        )
        observed_speed = flow_input.mean_speed_kmh
        speed_ratio = 1.0 if observed_speed is None else observed_speed / self.free_flow_speed_kmh
        density_ratio = density / self.jam_density_veh_per_km
        congestion_level = self._classify(density_ratio, speed_ratio)

        return TrafficFlowResult(
            flow_q_veh_per_hour=float(flow),
            density_k_veh_per_km=float(density),
            space_mean_speed_kmh=observed_speed,
            congestion_level=congestion_level,
            greenshields_speed_kmh=float(greenshields_speed),
            model_explanation=(
                "Greenshields model: v = vf * (1 - k/kj); "
                "LWR conservation law is used as defense-level wave propagation rationale."
            ),
        )

    @staticmethod
    def _classify(density_ratio: float, speed_ratio: float) -> str:
        if density_ratio < 0.25 and speed_ratio >= 0.65:
            return "free_flow"
        if 0.35 <= density_ratio <= 0.65 and 0.35 <= speed_ratio <= 0.65:
            return "critical_flow"
        if density_ratio >= 0.65 or speed_ratio < 0.35:
            return "congested_flow"
        return "stable_flow"
