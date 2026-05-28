from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class TrafficFlowInput:
    vehicle_count: int
    segment_length_m: float
    mean_speed_kmh: float | None
    observation_window_sec: float


@dataclass(frozen=True)
class TrafficFlowResult:
    flow_q_veh_per_hour: float
    density_k_veh_per_km: float
    space_mean_speed_kmh: float | None
    congestion_level: str
    greenshields_speed_kmh: float
    model_explanation: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
