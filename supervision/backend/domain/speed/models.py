from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SpeedRecord:
    tracker_id: int
    speed_kmh: float | None
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
    physics_valid: bool = True
    quality_label: str = "stable"
    rejection_reason: str | None = None
    track_age_frames: int = 0
    window_residual_m: float | None = None
    raw_speed_kmh: float | None = None
    speed_stability_score: float | None = None
    speed_cv: float | None = None
    max_speed_jump_kmh: float | None = None
    speed_jump_p95_kmh: float | None = None
    acceleration_p95_mps2: float | None = None
    jerk_p95_mps3: float | None = None
    stability_label: str | None = None
    position_sigma_m: float | None = None
    position_covariance: list[list[float]] | None = None
    measurement_source: str | None = None
    measurement_confidence: float | None = None
    local_scale_factor: float | None = None
    reconstructed: bool = False
    bev_risk_level: str | None = None
    bev_risk_reason: str | None = None
    local_scale_percentile: float | None = None
    contact_fusion_sources: list[str] | None = None
    contact_fusion_weights: dict[str, float] | None = None
    contact_pixel_covariance: list[list[float]] | None = None
    contact_fusion_confidence: float | None = None
    tracking_integrity_state: str | None = None
    id_switch_risk: float | None = None
    speed_frozen: bool = False
    integrity_rejection_reason: str | None = None


@dataclass
class TrackHistory:
    tracker_id: int
    positions: list[tuple[float, float]] = field(default_factory=list)
    timestamps: list[float] = field(default_factory=list)
    speeds_kmh: list[float] = field(default_factory=list)
    rejected_observations: int = 0
    displayed_speed_kmh: float | None = None
    displayed_timestamp_sec: float | None = None
    auxiliary_velocity_weight: float = 0.0
    measurement_confidences: list[float] = field(default_factory=list)
    position_sigmas_m: list[float] = field(default_factory=list)

    def add_position(
        self,
        position: tuple[float, float],
        timestamp_sec: float,
        measurement_confidence: float = 1.0,
        position_sigma_m: float = 0.0,
    ) -> None:
        self.positions.append(position)
        self.timestamps.append(timestamp_sec)
        self.measurement_confidences.append(max(0.05, min(1.0, measurement_confidence)))
        self.position_sigmas_m.append(max(0.0, position_sigma_m))

    @property
    def last_position(self) -> tuple[float, float] | None:
        return self.positions[-1] if self.positions else None

    @property
    def last_timestamp(self) -> float | None:
        return self.timestamps[-1] if self.timestamps else None
