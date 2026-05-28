from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SpeedRecord:
    tracker_id: int
    speed_kmh: float
    timestamp_sec: float
    world_x: float
    world_y: float
    speed_uncertainty_kmh: float | None = None
    speed_confidence: float | None = None
    position_rmse_m: float | None = None
    velocity_x_mps: float | None = None
    velocity_y_mps: float | None = None
    heading_deg: float | None = None
    acceleration_mps2: float | None = None


@dataclass
class TrackHistory:
    tracker_id: int
    positions: list[tuple[float, float]] = field(default_factory=list)
    timestamps: list[float] = field(default_factory=list)
    speeds_kmh: list[float] = field(default_factory=list)

    def add_position(self, position: tuple[float, float], timestamp_sec: float) -> None:
        self.positions.append(position)
        self.timestamps.append(timestamp_sec)

    @property
    def last_position(self) -> tuple[float, float] | None:
        return self.positions[-1] if self.positions else None

    @property
    def last_timestamp(self) -> float | None:
        return self.timestamps[-1] if self.timestamps else None
