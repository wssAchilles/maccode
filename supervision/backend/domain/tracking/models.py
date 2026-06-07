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
    calibration_speed_posterior: dict[str, object] | None = None
    joint_speed_posterior: dict[str, object] | None = None
    joint_physics_posterior: dict[str, object] | None = None
    motion_mode: str | None = None
    motion_mode_probability: float | None = None
    imm_speed_kmh: float | None = None
    tracklet_relinked: bool = False
    tracklet_parent_id: int | None = None
    association_score: float | None = None
    association_rejection_reason: str | None = None
    association_quality: float | None = None
    low_score_recovered: bool = False
    scale_confidence_label: str | None = None
    contact_outlier_source: str | None = None
    contact_innovation_score: float | None = None
    optical_flow_inlier_ratio: float | None = None
    optical_flow_velocity_covariance: list[list[float]] | None = None
    weak_calibration_reason: str | None = None
    adaptive_measurement_noise_multiplier: float | None = None
    innovation_nis: float | None = None
    perspective_speed_inflation_detected: bool = False
    speed_scale_correlation: float | None = None
    far_near_speed_ratio: float | None = None
    geometry_rejection_reason: str | None = None
    pedestrian_scale_drift_detected: bool = False
    speed_inverse_height_correlation: float | None = None
    height_consistency_score: float | None = None
    recommended_speed_scale_factor: float | None = None
    pedestrian_geometry_model_reference: str | None = None
    plane_id: str | None = None
    contact_source: str | None = None
    contact_state: str | None = None
    measurement_policy: str | None = None
    contact_state_probabilities: dict[str, float] | None = None
    world_position_covariance: list[list[float]] | None = None
    speed_geometry_diagnostics: dict[str, object] | None = None
    dominant_uncertainty_source: str | None = None
    physics_confidence: float | None = None
    calibration_confidence: float | None = None
    contact_confidence: float | None = None
    tracking_confidence: float | None = None
    occlusion_confidence: float | None = None
    dynamics_confidence: float | None = None
    confidence_rejection_reason: str | None = None

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
        calibration_speed_posterior: dict[str, object] | None = None,
        joint_speed_posterior: dict[str, object] | None = None,
        joint_physics_posterior: dict[str, object] | None = None,
        motion_mode: str | None = None,
        motion_mode_probability: float | None = None,
        imm_speed_kmh: float | None = None,
        tracklet_relinked: bool = False,
        tracklet_parent_id: int | None = None,
        association_score: float | None = None,
        association_rejection_reason: str | None = None,
        association_quality: float | None = None,
        low_score_recovered: bool = False,
        scale_confidence_label: str | None = None,
        contact_outlier_source: str | None = None,
        contact_innovation_score: float | None = None,
        optical_flow_inlier_ratio: float | None = None,
        optical_flow_velocity_covariance: list[list[float]] | None = None,
        weak_calibration_reason: str | None = None,
        adaptive_measurement_noise_multiplier: float | None = None,
        innovation_nis: float | None = None,
        perspective_speed_inflation_detected: bool = False,
        speed_scale_correlation: float | None = None,
        far_near_speed_ratio: float | None = None,
        geometry_rejection_reason: str | None = None,
        pedestrian_scale_drift_detected: bool = False,
        speed_inverse_height_correlation: float | None = None,
        height_consistency_score: float | None = None,
        recommended_speed_scale_factor: float | None = None,
        pedestrian_geometry_model_reference: str | None = None,
        plane_id: str | None = None,
        contact_source: str | None = None,
        contact_state: str | None = None,
        measurement_policy: str | None = None,
        contact_state_probabilities: dict[str, float] | None = None,
        world_position_covariance: list[list[float]] | None = None,
        speed_geometry_diagnostics: dict[str, object] | None = None,
        dominant_uncertainty_source: str | None = None,
        physics_confidence: float | None = None,
        calibration_confidence: float | None = None,
        contact_confidence: float | None = None,
        tracking_confidence: float | None = None,
        occlusion_confidence: float | None = None,
        dynamics_confidence: float | None = None,
        confidence_rejection_reason: str | None = None,
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
            calibration_speed_posterior=calibration_speed_posterior,
            joint_speed_posterior=joint_speed_posterior,
            joint_physics_posterior=joint_physics_posterior,
            motion_mode=motion_mode,
            motion_mode_probability=motion_mode_probability,
            imm_speed_kmh=imm_speed_kmh,
            tracklet_relinked=tracklet_relinked,
            tracklet_parent_id=tracklet_parent_id,
            association_score=association_score,
            association_rejection_reason=association_rejection_reason,
            association_quality=association_quality,
            low_score_recovered=low_score_recovered,
            scale_confidence_label=scale_confidence_label,
            contact_outlier_source=contact_outlier_source,
            contact_innovation_score=contact_innovation_score,
            optical_flow_inlier_ratio=optical_flow_inlier_ratio,
            optical_flow_velocity_covariance=optical_flow_velocity_covariance,
            weak_calibration_reason=weak_calibration_reason,
            adaptive_measurement_noise_multiplier=adaptive_measurement_noise_multiplier,
            innovation_nis=innovation_nis,
            perspective_speed_inflation_detected=perspective_speed_inflation_detected,
            speed_scale_correlation=speed_scale_correlation,
            far_near_speed_ratio=far_near_speed_ratio,
            geometry_rejection_reason=geometry_rejection_reason,
            pedestrian_scale_drift_detected=pedestrian_scale_drift_detected,
            speed_inverse_height_correlation=speed_inverse_height_correlation,
            height_consistency_score=height_consistency_score,
            recommended_speed_scale_factor=recommended_speed_scale_factor,
            pedestrian_geometry_model_reference=pedestrian_geometry_model_reference,
            plane_id=plane_id,
            contact_source=contact_source,
            contact_state=contact_state,
            measurement_policy=measurement_policy,
            contact_state_probabilities=contact_state_probabilities,
            world_position_covariance=world_position_covariance,
            speed_geometry_diagnostics=speed_geometry_diagnostics,
            dominant_uncertainty_source=dominant_uncertainty_source,
            physics_confidence=physics_confidence,
            calibration_confidence=calibration_confidence,
            contact_confidence=contact_confidence,
            tracking_confidence=tracking_confidence,
            occlusion_confidence=occlusion_confidence,
            dynamics_confidence=dynamics_confidence,
            confidence_rejection_reason=confidence_rejection_reason,
        )
