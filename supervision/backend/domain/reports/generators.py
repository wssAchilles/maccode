from __future__ import annotations

from statistics import mean

from shared.configs.constants import DEFAULT_REPORT_INTERVAL

from domain.reports.models import CumulativeStats, FrameReport
from domain.speed.models import SpeedRecord
from domain.tracking.models import Track
from domain.zones.models import ZoneStats


class ReportGenerator:
    def __init__(self, report_interval: int = DEFAULT_REPORT_INTERVAL) -> None:
        self.report_interval = report_interval
        self._frames: list[FrameReport] = []
        self._seen_track_ids: set[int] = set()

    def should_report(self, frame_index: int) -> bool:
        return frame_index % self.report_interval == 0

    def add_frame(
        self,
        frame_index: int,
        timestamp_sec: float,
        tracks: list[Track],
        zone_stats: list[ZoneStats],
        fps: float,
        speeds: dict[int, float | None] | None = None,
        speed_records: dict[int, SpeedRecord] | None = None,
        calibration_quality: str | None = None,
        calibration_diagnostics: dict[str, object] | None = None,
        homography_grid: dict[str, object] | None = None,
        traffic_flow: dict[str, object] | None = None,
        regional_people_count: dict[str, object] | None = None,
        infrastructure_semantics: dict[str, object] | None = None,
        safety_metrics: dict[str, object] | None = None,
        bev_confidence_map: dict[str, object] | None = None,
        integrity_diagnostics: dict[str, object] | None = None,
        calibration_sensitivity: dict[str, object] | None = None,
        confidence_calibration_summary: dict[str, object] | None = None,
        tracklet_reassociation_summary: dict[str, object] | None = None,
        model_comparison_benchmark: dict[str, object] | None = None,
        speed_nis_diagnostics: dict[str, object] | None = None,
        speed_geometry_diagnostics: dict[str, object] | None = None,
    ) -> FrameReport:
        speeds = speeds or {}
        speed_records = speed_records or {}
        tracks_with_speed = [
            self._apply_speed(track, speeds, speed_records) for track in tracks
        ]
        self._seen_track_ids.update(track.tracker_id for track in tracks_with_speed)
        report = FrameReport(
            frame_index=frame_index,
            timestamp_sec=timestamp_sec,
            fps=fps,
            active_tracks=tracks_with_speed,
            zone_stats=zone_stats,
            total_in=sum(stats.in_count for stats in zone_stats),
            total_out=sum(stats.out_count for stats in zone_stats),
            calibration_quality=calibration_quality,
            calibration_diagnostics=calibration_diagnostics,
            homography_grid=homography_grid,
            traffic_flow=traffic_flow,
            regional_people_count=regional_people_count,
            infrastructure_semantics=infrastructure_semantics,
            safety_metrics=safety_metrics,
            bev_confidence_map=bev_confidence_map,
            integrity_diagnostics=integrity_diagnostics,
            calibration_sensitivity=calibration_sensitivity,
            confidence_calibration_summary=confidence_calibration_summary,
            tracklet_reassociation_summary=tracklet_reassociation_summary,
            model_comparison_benchmark=model_comparison_benchmark,
            speed_nis_diagnostics=speed_nis_diagnostics,
            speed_geometry_diagnostics=speed_geometry_diagnostics,
        )
        self._frames.append(report)
        return report

    def generate_cumulative_stats(self) -> CumulativeStats:
        if not self._frames:
            return CumulativeStats(0, 0, [], 0.0, None, 0.0)

        speeds = [
            track.speed_kmh
            for frame in self._frames
            for track in frame.active_tracks
            if track.speed_kmh is not None and track.physics_valid
        ]
        confidences = [
            track.speed_confidence
            for frame in self._frames
            for track in frame.active_tracks
            if track.speed_confidence is not None and track.physics_valid
        ]
        last_frame = self._frames[-1]
        return CumulativeStats(
            total_frames=len(self._frames),
            total_unique_tracks=len(self._seen_track_ids),
            zone_stats=last_frame.zone_stats,
            avg_fps=mean(frame.fps for frame in self._frames),
            avg_speed_kmh=mean(speeds) if speeds else None,
            processing_time_sec=last_frame.timestamp_sec - self._frames[0].timestamp_sec,
            avg_speed_confidence=mean(confidences) if confidences else None,
        )

    def reset(self) -> None:
        self._frames.clear()
        self._seen_track_ids.clear()

    @staticmethod
    def _apply_speed(
        track: Track,
        speeds: dict[int, float | None],
        speed_records: dict[int, SpeedRecord],
    ) -> Track:
        record = speed_records.get(track.tracker_id)
        if record is not None:
            return track.with_speed(
                record.speed_kmh,
                speed_uncertainty_kmh=record.speed_uncertainty_kmh,
                speed_confidence=record.speed_confidence,
                speed_confidence_interval_kmh=ReportGenerator._confidence_interval(record),
                position_rmse_m=record.position_rmse_m,
                ground_x_m=record.world_x,
                ground_y_m=record.world_y,
                velocity_x_mps=record.velocity_x_mps,
                velocity_y_mps=record.velocity_y_mps,
                heading_deg=record.heading_deg,
                acceleration_mps2=record.acceleration_mps2,
                physics_valid=record.physics_valid,
                quality_label=record.quality_label,
                rejection_reason=record.rejection_reason,
                track_age_frames=record.track_age_frames,
                window_residual_m=record.window_residual_m,
                raw_speed_kmh=record.raw_speed_kmh,
                speed_stability_score=record.speed_stability_score,
                speed_cv=record.speed_cv,
                max_speed_jump_kmh=record.max_speed_jump_kmh,
                speed_jump_p95_kmh=record.speed_jump_p95_kmh,
                acceleration_p95_mps2=record.acceleration_p95_mps2,
                jerk_p95_mps3=record.jerk_p95_mps3,
                stability_label=record.stability_label,
                position_sigma_m=record.position_sigma_m,
                position_covariance=record.position_covariance,
                measurement_source=record.measurement_source,
                measurement_confidence=record.measurement_confidence,
                local_scale_factor=record.local_scale_factor,
                reconstructed=record.reconstructed,
                bev_risk_level=record.bev_risk_level,
                bev_risk_reason=record.bev_risk_reason,
                local_scale_percentile=record.local_scale_percentile,
                contact_fusion_sources=record.contact_fusion_sources,
                contact_fusion_weights=record.contact_fusion_weights,
                contact_pixel_covariance=record.contact_pixel_covariance,
                contact_fusion_confidence=record.contact_fusion_confidence,
                tracking_integrity_state=record.tracking_integrity_state,
                id_switch_risk=record.id_switch_risk,
                speed_frozen=record.speed_frozen,
                integrity_rejection_reason=record.integrity_rejection_reason,
                speed_confidence_calibrated=record.speed_confidence_calibrated,
                confidence_calibration_bin=record.confidence_calibration_bin,
                calibration_uncertainty_band_kmh=record.calibration_uncertainty_band_kmh,
                calibration_speed_posterior=record.calibration_speed_posterior,
                joint_speed_posterior=record.joint_speed_posterior,
                joint_physics_posterior=record.joint_physics_posterior,
                motion_mode=record.motion_mode,
                motion_mode_probability=record.motion_mode_probability,
                imm_speed_kmh=record.imm_speed_kmh,
                tracklet_relinked=record.tracklet_relinked,
                tracklet_parent_id=record.tracklet_parent_id,
                association_score=record.association_score,
                association_rejection_reason=record.association_rejection_reason,
                association_quality=record.association_quality,
                low_score_recovered=record.low_score_recovered,
                scale_confidence_label=record.scale_confidence_label,
                contact_outlier_source=record.contact_outlier_source,
                contact_innovation_score=record.contact_innovation_score,
                optical_flow_inlier_ratio=record.optical_flow_inlier_ratio,
                optical_flow_velocity_covariance=record.optical_flow_velocity_covariance,
                weak_calibration_reason=record.weak_calibration_reason,
                adaptive_measurement_noise_multiplier=(
                    record.adaptive_measurement_noise_multiplier
                ),
                innovation_nis=record.innovation_nis,
                perspective_speed_inflation_detected=(
                    record.perspective_speed_inflation_detected
                ),
                speed_scale_correlation=record.speed_scale_correlation,
                far_near_speed_ratio=record.far_near_speed_ratio,
                geometry_rejection_reason=record.geometry_rejection_reason,
                pedestrian_scale_drift_detected=record.pedestrian_scale_drift_detected,
                speed_inverse_height_correlation=record.speed_inverse_height_correlation,
                height_consistency_score=record.height_consistency_score,
                recommended_speed_scale_factor=record.recommended_speed_scale_factor,
                pedestrian_geometry_model_reference=(
                    record.pedestrian_geometry_model_reference
                ),
                plane_id=record.plane_id,
                contact_source=record.contact_source,
                contact_state=record.contact_state,
                measurement_policy=record.measurement_policy,
                contact_state_probabilities=record.contact_state_probabilities,
                world_position_covariance=record.world_position_covariance,
                speed_geometry_diagnostics=record.speed_geometry_diagnostics,
                dominant_uncertainty_source=record.dominant_uncertainty_source,
                physics_confidence=record.physics_confidence,
                calibration_confidence=record.calibration_confidence,
                contact_confidence=record.contact_confidence,
                tracking_confidence=record.tracking_confidence,
                occlusion_confidence=record.occlusion_confidence,
                dynamics_confidence=record.dynamics_confidence,
                confidence_rejection_reason=record.confidence_rejection_reason,
                body_ground_projection=record.body_ground_projection,
                support_contact_anchor=record.support_contact_anchor,
                contact_phase_probabilities=record.contact_phase_probabilities,
                foot_skate_risk=record.foot_skate_risk,
                pedestrian_periodic_calibration_consistency=(
                    record.pedestrian_periodic_calibration_consistency
                ),
                near_far_speed_drift_metrics=record.near_far_speed_drift_metrics,
            )
        if track.tracker_id in speeds:
            return track.with_speed(speeds[track.tracker_id])
        return track

    @staticmethod
    def _confidence_interval(record: SpeedRecord) -> list[float] | None:
        if (
            record.speed_kmh is None
            or record.speed_uncertainty_kmh is None
            or not record.physics_valid
        ):
            return None
        lower = max(0.0, record.speed_kmh - record.speed_uncertainty_kmh)
        upper = record.speed_kmh + record.speed_uncertainty_kmh
        return [float(lower), float(upper)]
