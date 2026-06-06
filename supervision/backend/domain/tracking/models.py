from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class Track:
    tracker_id: int
    class_id: int
    class_name: str
    confidence: float
    xyxy: list[float]
    first_seen_frame: int
    last_seen_frame: int
    speed_kmh: float | None = None
    speed_uncertainty_kmh: float | None = None
    speed_confidence: float | None = None
    speed_confidence_interval_kmh: list[float] | None = None
    position_rmse_m: float | None = None
    ground_x_m: float | None = None
    ground_y_m: float | None = None
    velocity_x_mps: float | None = None
    velocity_y_mps: float | None = None
    heading_deg: float | None = None
    acceleration_mps2: float | None = None
    physics_valid: bool = False
    quality_label: str = "not_applicable"
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
    speed_confidence_calibrated: float | None = None
    confidence_calibration_bin: str | None = None
    calibration_uncertainty_band_kmh: list[float | None] | None = None
    motion_mode: str | None = None
    motion_mode_probability: float | None = None
    imm_speed_kmh: float | None = None
    tracklet_relinked: bool = False
    tracklet_parent_id: int | None = None
    association_score: float | None = None
    association_rejection_reason: str | None = None

    @property
    def center(self) -> tuple[float, float]:
        x1, y1, x2, y2 = self.xyxy
        return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)

    @property
    def bottom_center(self) -> tuple[float, float]:
        x1, _, x2, y2 = self.xyxy
        return ((x1 + x2) / 2.0, y2)

    def with_detection(self, xyxy: list[float], confidence: float, frame_index: int) -> Track:
        return replace(
            self,
            xyxy=list(xyxy),
            confidence=confidence,
            last_seen_frame=frame_index,
        )

    def with_speed(
        self,
        speed_kmh: float | None,
        speed_uncertainty_kmh: float | None = None,
        speed_confidence: float | None = None,
        speed_confidence_interval_kmh: list[float] | None = None,
        position_rmse_m: float | None = None,
        ground_x_m: float | None = None,
        ground_y_m: float | None = None,
        velocity_x_mps: float | None = None,
        velocity_y_mps: float | None = None,
        heading_deg: float | None = None,
        acceleration_mps2: float | None = None,
        physics_valid: bool = True,
        quality_label: str = "stable",
        rejection_reason: str | None = None,
        track_age_frames: int = 0,
        window_residual_m: float | None = None,
        raw_speed_kmh: float | None = None,
        speed_stability_score: float | None = None,
        speed_cv: float | None = None,
        max_speed_jump_kmh: float | None = None,
        speed_jump_p95_kmh: float | None = None,
        acceleration_p95_mps2: float | None = None,
        jerk_p95_mps3: float | None = None,
        stability_label: str | None = None,
        position_sigma_m: float | None = None,
        position_covariance: list[list[float]] | None = None,
        measurement_source: str | None = None,
        measurement_confidence: float | None = None,
        local_scale_factor: float | None = None,
        reconstructed: bool = False,
        bev_risk_level: str | None = None,
        bev_risk_reason: str | None = None,
        local_scale_percentile: float | None = None,
        contact_fusion_sources: list[str] | None = None,
        contact_fusion_weights: dict[str, float] | None = None,
        contact_pixel_covariance: list[list[float]] | None = None,
        contact_fusion_confidence: float | None = None,
        tracking_integrity_state: str | None = None,
        id_switch_risk: float | None = None,
        speed_frozen: bool = False,
        integrity_rejection_reason: str | None = None,
        speed_confidence_calibrated: float | None = None,
        confidence_calibration_bin: str | None = None,
        calibration_uncertainty_band_kmh: list[float | None] | None = None,
        motion_mode: str | None = None,
        motion_mode_probability: float | None = None,
        imm_speed_kmh: float | None = None,
        tracklet_relinked: bool = False,
        tracklet_parent_id: int | None = None,
        association_score: float | None = None,
        association_rejection_reason: str | None = None,
    ) -> Track:
        return replace(
            self,
            speed_kmh=speed_kmh,
            speed_uncertainty_kmh=speed_uncertainty_kmh,
            speed_confidence=speed_confidence,
            speed_confidence_interval_kmh=speed_confidence_interval_kmh,
            position_rmse_m=position_rmse_m,
            ground_x_m=ground_x_m,
            ground_y_m=ground_y_m,
            velocity_x_mps=velocity_x_mps,
            velocity_y_mps=velocity_y_mps,
            heading_deg=heading_deg,
            acceleration_mps2=acceleration_mps2,
            physics_valid=physics_valid,
            quality_label=quality_label,
            rejection_reason=rejection_reason,
            track_age_frames=track_age_frames,
            window_residual_m=window_residual_m,
            raw_speed_kmh=raw_speed_kmh,
            speed_stability_score=speed_stability_score,
            speed_cv=speed_cv,
            max_speed_jump_kmh=max_speed_jump_kmh,
            speed_jump_p95_kmh=speed_jump_p95_kmh,
            acceleration_p95_mps2=acceleration_p95_mps2,
            jerk_p95_mps3=jerk_p95_mps3,
            stability_label=stability_label,
            position_sigma_m=position_sigma_m,
            position_covariance=position_covariance,
            measurement_source=measurement_source,
            measurement_confidence=measurement_confidence,
            local_scale_factor=local_scale_factor,
            reconstructed=reconstructed,
            bev_risk_level=bev_risk_level,
            bev_risk_reason=bev_risk_reason,
            local_scale_percentile=local_scale_percentile,
            contact_fusion_sources=contact_fusion_sources,
            contact_fusion_weights=contact_fusion_weights,
            contact_pixel_covariance=contact_pixel_covariance,
            contact_fusion_confidence=contact_fusion_confidence,
            tracking_integrity_state=tracking_integrity_state,
            id_switch_risk=id_switch_risk,
            speed_frozen=speed_frozen,
            integrity_rejection_reason=integrity_rejection_reason,
            speed_confidence_calibrated=speed_confidence_calibrated,
            confidence_calibration_bin=confidence_calibration_bin,
            calibration_uncertainty_band_kmh=calibration_uncertainty_band_kmh,
            motion_mode=motion_mode,
            motion_mode_probability=motion_mode_probability,
            imm_speed_kmh=imm_speed_kmh,
            tracklet_relinked=tracklet_relinked,
            tracklet_parent_id=tracklet_parent_id,
            association_score=association_score,
            association_rejection_reason=association_rejection_reason,
        )
