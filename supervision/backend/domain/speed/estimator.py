from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Any, cast

import numpy as np
from numpy.typing import NDArray
from shared.configs.constants import DEFAULT_MAX_SPEED_KMH, DEFAULT_MIN_DISPLACEMENT_M

from domain.motion.models import MotionProfile
from domain.speed.adaptive_noise import AdaptiveMeasurementNoiseController
from domain.speed.filters import max_speed_filter, min_displacement_filter
from domain.speed.kalman import (
    ConstantAccelerationKalmanFilter2D,
    KalmanFilter2D,
    MetricGroundSpeedFilter,
    kalman_config_for_motion_profile,
)
from domain.speed.models import SpeedRecord, TrackHistory
from domain.speed.pedestrian_scale_drift import (
    PedestrianGeometrySample,
    PedestrianScaleDriftAnalyzer,
    PedestrianScaleDriftResult,
)
from domain.speed.perspective_guard import (
    PerspectiveGuardResult,
    PerspectiveGuardSample,
    PerspectiveSpeedInflationDetector,
)
from domain.speed.smoothing import median_smoothing
from domain.speed.uncertainty import estimate_speed_uncertainty
from domain.speed.view_transformer import LocalPositionUncertainty, ViewTransformer

MAHALANOBIS_ID_SWITCH_THRESHOLD_D2 = 9.21
PINV_MAHALANOBIS_ID_SWITCH_THRESHOLD_D2 = 6.0


@dataclass(frozen=True)
class _RegressionState:
    velocity_mps: tuple[float, float]
    speed_kmh: float
    duration_sec: float
    displacement_m: float
    residual_m: float


class SpeedEstimator:
    def __init__(
        self,
        view_transformer: ViewTransformer,
        smoothing_window: int = 5,
        min_displacement_m: float = DEFAULT_MIN_DISPLACEMENT_M,
        max_speed_kmh: float = DEFAULT_MAX_SPEED_KMH,
        position_rmse_m: float = 0.1,
        timestamp_uncertainty_sec: float = 0.0,
    ) -> None:
        self.view_transformer = view_transformer
        self.smoothing_window = smoothing_window
        self.min_displacement_m = min_displacement_m
        self.max_speed_kmh = max_speed_kmh
        self.position_rmse_m = position_rmse_m
        self.timestamp_uncertainty_sec = timestamp_uncertainty_sec
        self._histories: dict[int, TrackHistory] = {}
        self._latest_records: dict[int, SpeedRecord] = {}
        self._kalman_filters: dict[
            int,
            KalmanFilter2D | MetricGroundSpeedFilter | ConstantAccelerationKalmanFilter2D,
        ] = {}
        self._adaptive_noise_controllers: dict[int, AdaptiveMeasurementNoiseController] = {}
        self._perspective_samples: dict[int, list[PerspectiveGuardSample]] = {}
        self._perspective_guard = PerspectiveSpeedInflationDetector()
        self._pedestrian_geometry_samples: dict[int, list[PedestrianGeometrySample]] = {}
        self._pedestrian_scale_drift = PedestrianScaleDriftAnalyzer()

    def update(
        self,
        tracker_id: int,
        pixel_center: tuple[float, float],
        timestamp_sec: float,
        process_noise: str | None = None,
        motion_profile: MotionProfile | None = None,
        detection_confidence: float = 1.0,
        measurement_confidence: float = 1.0,
        pixel_sigma_px: float = 1.0,
        measurement_source: str | None = None,
        auxiliary_velocity_mps: tuple[float, float] | None = None,
        auxiliary_confidence: float = 0.0,
        pixel_covariance_px: list[list[float]] | None = None,
        local_scale_percentile: float | None = None,
        bbox_xyxy: list[float] | None = None,
        bbox_height_px: float | None = None,
        pose_ankle_pixel: tuple[float, float] | None = None,
        pose_head_pixel: tuple[float, float] | None = None,
        plane_id: str | None = None,
        speed_geometry_diagnostics: dict[str, object] | None = None,
    ) -> float | None:
        if motion_profile is None:
            return self._legacy_update(
                tracker_id,
                pixel_center,
                timestamp_sec,
                process_noise=process_noise,
            )
        if not motion_profile.should_estimate_speed:
            return None
        world_position = self.view_transformer.transform_point(*pixel_center)
        local_uncertainty = self.view_transformer.local_position_uncertainty(
            pixel_center[0],
            pixel_center[1],
            pixel_sigma=max(pixel_sigma_px, 0.0),
        )
        effective_position_rmse_m = max(
            self.position_rmse_m,
            local_uncertainty.position_sigma_m,
        )
        bounded_measurement_confidence = max(0.05, min(1.0, measurement_confidence))
        measurement_noise = max(
            1e-6,
            (effective_position_rmse_m**2) / bounded_measurement_confidence,
        )
        measurement_covariance = self._measurement_covariance(
            pixel_center,
            local_uncertainty,
            measurement_noise,
            pixel_covariance_px,
        )
        position_covariance = measurement_covariance.tolist()
        adaptive_controller = self._adaptive_noise_controllers.setdefault(
            tracker_id,
            AdaptiveMeasurementNoiseController(),
        )
        adaptive_measurement_noise = measurement_covariance * adaptive_controller.multiplier
        history = self._histories.setdefault(tracker_id, TrackHistory(tracker_id))
        previous_position = history.last_position
        previous_timestamp = history.last_timestamp

        if previous_position is None or previous_timestamp is None:
            history.add_position(
                world_position,
                timestamp_sec,
                bounded_measurement_confidence,
                local_uncertainty.position_sigma_m,
                local_scale_percentile,
            )
            self._kalman_filters.setdefault(
                tracker_id,
                MetricGroundSpeedFilter(
                    kalman_config_for_motion_profile(motion_profile.process_noise),
                ),
            ).update(
                world_position,
                timestamp_sec,
                measurement_noise=adaptive_measurement_noise,
            )
            self._latest_records[tracker_id] = self._quality_record(
                tracker_id=tracker_id,
                timestamp_sec=timestamp_sec,
                world_position=world_position,
                motion_profile=motion_profile,
                quality_label="warming_up",
                rejection_reason=None,
                position_rmse_m=effective_position_rmse_m,
                position_sigma_m=local_uncertainty.position_sigma_m,
                position_covariance=position_covariance,
                measurement_source=measurement_source,
                measurement_confidence=bounded_measurement_confidence,
                local_scale_factor=local_uncertainty.local_scale_factor,
                local_scale_percentile=local_scale_percentile,
                plane_id=plane_id,
                contact_source=measurement_source,
                world_position_covariance=position_covariance,
                speed_geometry_diagnostics=speed_geometry_diagnostics,
                adaptive_measurement_noise_multiplier=adaptive_controller.multiplier,
                innovation_nis=None,
            )
            return None

        delta_t = timestamp_sec - previous_timestamp
        if delta_t <= 0:
            return None

        displacement = math.dist(previous_position, world_position)
        instantaneous_speed_kmh = displacement / delta_t * 3.6
        hard_max_speed = motion_profile.hard_max_speed_kmh or motion_profile.max_speed_kmh
        if instantaneous_speed_kmh > hard_max_speed:
            history.rejected_observations += 1
            hard_rejection_reason = self._hard_speed_rejection_reason(motion_profile)
            perspective_result = self._instant_perspective_result(
                instantaneous_speed_kmh,
                local_scale_percentile,
                motion_profile,
            )
            pedestrian_result = self._update_pedestrian_scale_drift(
                tracker_id=tracker_id,
                speed_kmh=instantaneous_speed_kmh,
                pixel_center=pixel_center,
                local_scale_factor=local_uncertainty.local_scale_factor,
                local_scale_percentile=local_scale_percentile,
                motion_profile=motion_profile,
                timestamp_sec=timestamp_sec,
                bbox_xyxy=bbox_xyxy,
                bbox_height_px=bbox_height_px,
                pose_ankle_pixel=pose_ankle_pixel,
                pose_head_pixel=pose_head_pixel,
            )
            self._latest_records[tracker_id] = self._quality_record(
                tracker_id=tracker_id,
                timestamp_sec=timestamp_sec,
                world_position=world_position,
                motion_profile=motion_profile,
                quality_label=(
                    "geometry_invalid"
                    if (
                        perspective_result.perspective_speed_inflation_detected
                        or pedestrian_result.scale_drift_detected
                    )
                    else "rejected"
                ),
                rejection_reason=(
                    pedestrian_result.geometry_rejection_reason
                    if pedestrian_result.scale_drift_detected
                    else
                    perspective_result.geometry_rejection_reason
                    or hard_rejection_reason
                ),
                position_rmse_m=effective_position_rmse_m,
                position_sigma_m=local_uncertainty.position_sigma_m,
                position_covariance=position_covariance,
                measurement_source=measurement_source,
                measurement_confidence=bounded_measurement_confidence,
                local_scale_factor=local_uncertainty.local_scale_factor,
                local_scale_percentile=local_scale_percentile,
                plane_id=plane_id,
                contact_source=measurement_source,
                world_position_covariance=position_covariance,
                speed_geometry_diagnostics=speed_geometry_diagnostics,
                adaptive_measurement_noise_multiplier=adaptive_controller.multiplier,
                innovation_nis=None,
                perspective_result=perspective_result,
                pedestrian_result=pedestrian_result,
            )
            return None

        kalman_filter = self._kalman_filters.setdefault(
            tracker_id,
            MetricGroundSpeedFilter(
                kalman_config_for_motion_profile(motion_profile.process_noise),
            ),
        )
        try:
            predicted_measurement = kalman_filter.predict_measurement(
                world_position,
                timestamp_sec,
                measurement_noise=adaptive_measurement_noise,
            )
        except TypeError:
            predicted_measurement = kalman_filter.predict_measurement(
                world_position,
                timestamp_sec,
            )
        innovation_nis = predicted_measurement.mahalanobis_d2
        mahalanobis_threshold = (
            PINV_MAHALANOBIS_ID_SWITCH_THRESHOLD_D2
            if predicted_measurement.covariance_solver == "pinv"
            else MAHALANOBIS_ID_SWITCH_THRESHOLD_D2
        )
        if predicted_measurement.mahalanobis_d2 > mahalanobis_threshold:
            history.rejected_observations += 1
            self._latest_records[tracker_id] = self._quality_record(
                tracker_id=tracker_id,
                timestamp_sec=timestamp_sec,
                world_position=world_position,
                motion_profile=motion_profile,
                quality_label="rejected",
                rejection_reason="mahalanobis_gate",
                position_rmse_m=effective_position_rmse_m,
                position_sigma_m=local_uncertainty.position_sigma_m,
                position_covariance=position_covariance,
                measurement_source=measurement_source,
                measurement_confidence=bounded_measurement_confidence,
                local_scale_factor=local_uncertainty.local_scale_factor,
                local_scale_percentile=local_scale_percentile,
                plane_id=plane_id,
                contact_source=measurement_source,
                world_position_covariance=position_covariance,
                speed_geometry_diagnostics=speed_geometry_diagnostics,
                adaptive_measurement_noise_multiplier=adaptive_controller.multiplier,
                innovation_nis=innovation_nis,
            )
            return None

        adaptive_state = adaptive_controller.update(innovation_nis)
        adaptive_measurement_noise = measurement_covariance * adaptive_state.multiplier

        history.add_position(
            world_position,
            timestamp_sec,
            bounded_measurement_confidence,
            local_uncertainty.position_sigma_m,
            local_scale_percentile,
        )
        kalman_state = kalman_filter.update(
            world_position,
            timestamp_sec,
            measurement_noise=adaptive_measurement_noise,
        )
        track_age = len(history.positions)
        if track_age < motion_profile.min_track_age_frames:
            self._latest_records[tracker_id] = self._quality_record(
                tracker_id=tracker_id,
                timestamp_sec=timestamp_sec,
                world_position=world_position,
                motion_profile=motion_profile,
                quality_label="warming_up",
                rejection_reason=None,
                position_rmse_m=effective_position_rmse_m,
                position_sigma_m=local_uncertainty.position_sigma_m,
                position_covariance=position_covariance,
                measurement_source=measurement_source,
                measurement_confidence=bounded_measurement_confidence,
                local_scale_factor=local_uncertainty.local_scale_factor,
                local_scale_percentile=local_scale_percentile,
                plane_id=plane_id,
                contact_source=measurement_source,
                world_position_covariance=position_covariance,
                speed_geometry_diagnostics=speed_geometry_diagnostics,
                adaptive_measurement_noise_multiplier=adaptive_state.multiplier,
                innovation_nis=innovation_nis,
            )
            return None

        regression = self._fit_window(history, motion_profile.regression_window_sec)
        if regression is None:
            self._latest_records[tracker_id] = self._quality_record(
                tracker_id=tracker_id,
                timestamp_sec=timestamp_sec,
                world_position=world_position,
                motion_profile=motion_profile,
                quality_label="warming_up",
                rejection_reason=None,
                position_rmse_m=effective_position_rmse_m,
                position_sigma_m=local_uncertainty.position_sigma_m,
                position_covariance=position_covariance,
                measurement_source=measurement_source,
                measurement_confidence=bounded_measurement_confidence,
                local_scale_factor=local_uncertainty.local_scale_factor,
                local_scale_percentile=local_scale_percentile,
                plane_id=plane_id,
                contact_source=measurement_source,
                world_position_covariance=position_covariance,
                speed_geometry_diagnostics=speed_geometry_diagnostics,
                adaptive_measurement_noise_multiplier=adaptive_state.multiplier,
                innovation_nis=innovation_nis,
            )
            return None

        state_velocity = kalman_state.velocity_mps
        state_speed_kmh = kalman_state.speed_kmh
        if (
            state_speed_kmh > 1e-6
            and regression.speed_kmh > 1e-6
            and self._velocity_angle_deg(state_velocity, regression.velocity_mps) <= 35.0
            and abs(state_speed_kmh - regression.speed_kmh) / max(regression.speed_kmh, 1.0)
            <= 0.45
        ):
            regression_velocity = (
                regression.velocity_mps[0] * 0.55 + state_velocity[0] * 0.45,
                regression.velocity_mps[1] * 0.55 + state_velocity[1] * 0.45,
            )
            regression = _RegressionState(
                velocity_mps=regression_velocity,
                speed_kmh=self._speed_kmh(regression_velocity),
                duration_sec=regression.duration_sec,
                displacement_m=regression.displacement_m,
                residual_m=regression.residual_m,
            )

        fused_velocity_mps, auxiliary_weight = self._fuse_velocity(
            regression.velocity_mps,
            auxiliary_velocity_mps,
            auxiliary_confidence,
            regression.residual_m,
            motion_profile,
        )
        fused_speed_kmh = self._speed_kmh(fused_velocity_mps)
        if fused_speed_kmh > hard_max_speed:
            history.rejected_observations += 1
            hard_rejection_reason = self._hard_speed_rejection_reason(motion_profile)
            perspective_result = self._update_perspective_guard(
                tracker_id=tracker_id,
                speed_kmh=fused_speed_kmh,
                pixel_y=pixel_center[1],
                local_scale_factor=local_uncertainty.local_scale_factor,
                local_scale_percentile=local_scale_percentile,
                timestamp_sec=timestamp_sec,
                motion_profile=motion_profile,
            )
            pedestrian_result = self._update_pedestrian_scale_drift(
                tracker_id=tracker_id,
                speed_kmh=fused_speed_kmh,
                pixel_center=pixel_center,
                local_scale_factor=local_uncertainty.local_scale_factor,
                local_scale_percentile=local_scale_percentile,
                motion_profile=motion_profile,
                timestamp_sec=timestamp_sec,
                bbox_xyxy=bbox_xyxy,
                bbox_height_px=bbox_height_px,
                pose_ankle_pixel=pose_ankle_pixel,
                pose_head_pixel=pose_head_pixel,
            )
            self._latest_records[tracker_id] = self._quality_record(
                tracker_id=tracker_id,
                timestamp_sec=timestamp_sec,
                world_position=world_position,
                motion_profile=motion_profile,
                quality_label=(
                    "geometry_invalid"
                    if (
                        perspective_result.perspective_speed_inflation_detected
                        or pedestrian_result.scale_drift_detected
                    )
                    else "rejected"
                ),
                rejection_reason=(
                    pedestrian_result.geometry_rejection_reason
                    if pedestrian_result.scale_drift_detected
                    else
                    perspective_result.geometry_rejection_reason
                    or hard_rejection_reason
                ),
                window_residual_m=regression.residual_m,
                position_rmse_m=effective_position_rmse_m,
                position_sigma_m=local_uncertainty.position_sigma_m,
                position_covariance=position_covariance,
                measurement_source=measurement_source,
                measurement_confidence=bounded_measurement_confidence,
                local_scale_factor=local_uncertainty.local_scale_factor,
                local_scale_percentile=local_scale_percentile,
                plane_id=plane_id,
                contact_source=measurement_source,
                world_position_covariance=position_covariance,
                speed_geometry_diagnostics=speed_geometry_diagnostics,
                adaptive_measurement_noise_multiplier=adaptive_state.multiplier,
                innovation_nis=innovation_nis,
                perspective_result=perspective_result,
                pedestrian_result=pedestrian_result,
            )
            return None

        perspective_result = self._update_perspective_guard(
            tracker_id=tracker_id,
            speed_kmh=fused_speed_kmh,
            pixel_y=pixel_center[1],
            local_scale_factor=local_uncertainty.local_scale_factor,
            local_scale_percentile=local_scale_percentile,
            timestamp_sec=timestamp_sec,
            motion_profile=motion_profile,
        )
        pedestrian_result = self._update_pedestrian_scale_drift(
            tracker_id=tracker_id,
            speed_kmh=fused_speed_kmh,
            pixel_center=pixel_center,
            local_scale_factor=local_uncertainty.local_scale_factor,
            local_scale_percentile=local_scale_percentile,
            motion_profile=motion_profile,
            timestamp_sec=timestamp_sec,
            bbox_xyxy=bbox_xyxy,
            bbox_height_px=bbox_height_px,
            pose_ankle_pixel=pose_ankle_pixel,
            pose_head_pixel=pose_head_pixel,
        )
        if (
            motion_profile.category == "low_inertia_dynamic"
            and pedestrian_result.scale_drift_detected
        ):
            history.rejected_observations += 1
            self._latest_records[tracker_id] = self._quality_record(
                tracker_id=tracker_id,
                timestamp_sec=timestamp_sec,
                world_position=world_position,
                motion_profile=motion_profile,
                quality_label="geometry_invalid",
                rejection_reason="pedestrian_perspective_scale_drift",
                window_residual_m=regression.residual_m,
                position_rmse_m=effective_position_rmse_m,
                position_sigma_m=local_uncertainty.position_sigma_m,
                position_covariance=position_covariance,
                measurement_source=measurement_source,
                measurement_confidence=bounded_measurement_confidence,
                local_scale_factor=local_uncertainty.local_scale_factor,
                local_scale_percentile=local_scale_percentile,
                plane_id=plane_id,
                contact_source=measurement_source,
                world_position_covariance=position_covariance,
                speed_geometry_diagnostics=speed_geometry_diagnostics,
                adaptive_measurement_noise_multiplier=adaptive_state.multiplier,
                innovation_nis=innovation_nis,
                perspective_result=perspective_result,
                pedestrian_result=pedestrian_result,
            )
            return None
        if (
            motion_profile.category == "low_inertia_dynamic"
            and perspective_result.perspective_speed_inflation_detected
        ):
            history.rejected_observations += 1
            self._latest_records[tracker_id] = self._quality_record(
                tracker_id=tracker_id,
                timestamp_sec=timestamp_sec,
                world_position=world_position,
                motion_profile=motion_profile,
                quality_label="geometry_invalid",
                rejection_reason="perspective_speed_inflation",
                window_residual_m=regression.residual_m,
                position_rmse_m=effective_position_rmse_m,
                position_sigma_m=local_uncertainty.position_sigma_m,
                position_covariance=position_covariance,
                measurement_source=measurement_source,
                measurement_confidence=bounded_measurement_confidence,
                local_scale_factor=local_uncertainty.local_scale_factor,
                local_scale_percentile=local_scale_percentile,
                plane_id=plane_id,
                contact_source=measurement_source,
                world_position_covariance=position_covariance,
                speed_geometry_diagnostics=speed_geometry_diagnostics,
                adaptive_measurement_noise_multiplier=adaptive_state.multiplier,
                innovation_nis=innovation_nis,
                perspective_result=perspective_result,
                pedestrian_result=pedestrian_result,
            )
            return None

        uncertainty_cap = max(8.0, motion_profile.max_speed_kmh * 0.35)
        uncertainty = estimate_speed_uncertainty(
            displacement_m=max((fused_speed_kmh / 3.6) * regression.duration_sec, 1e-6),
            delta_t_sec=regression.duration_sec,
            position_rmse_m=effective_position_rmse_m,
            timestamp_uncertainty_sec=self.timestamp_uncertainty_sec,
            residual_m=regression.residual_m,
            detection_confidence=min(1.0, detection_confidence + auxiliary_weight * 0.2),
            measurement_confidence=bounded_measurement_confidence,
            local_scale_factor=local_uncertainty.local_scale_factor,
            position_sigma_m=local_uncertainty.position_sigma_m,
            track_age_frames=track_age,
            min_track_age_frames=motion_profile.min_track_age_frames,
            uncertainty_cap_kmh=uncertainty_cap,
        )
        speed_confidence = min(uncertainty.speed_confidence, kalman_state.speed_confidence)
        if (
            fused_speed_kmh > motion_profile.max_speed_kmh
            or speed_confidence < motion_profile.confidence_floor
            or uncertainty.was_capped
        ):
            pedestrian_outlier = (
                motion_profile.category == "low_inertia_dynamic"
                and fused_speed_kmh > motion_profile.max_speed_kmh
            )
            pedestrian_far_speed = (
                pedestrian_outlier and (local_scale_percentile or 0.0) >= 0.80
            )
            if pedestrian_far_speed and not pedestrian_result.scale_drift_detected:
                pedestrian_result = PedestrianScaleDriftResult(
                    True,
                    pedestrian_result.speed_scale_correlation,
                    pedestrian_result.speed_inverse_height_correlation,
                    pedestrian_result.far_near_speed_ratio,
                    pedestrian_result.height_consistency_score,
                    pedestrian_result.recommended_speed_scale_factor,
                    "pedestrian_perspective_scale_drift",
                )
            self._latest_records[tracker_id] = self._quality_record(
                tracker_id=tracker_id,
                timestamp_sec=timestamp_sec,
                world_position=world_position,
                motion_profile=motion_profile,
                quality_label=(
                    "geometry_invalid"
                    if pedestrian_far_speed
                    else "pedestrian_speed_outlier"
                    if pedestrian_outlier
                    else "low_confidence"
                ),
                rejection_reason=(
                    "pedestrian_perspective_scale_drift"
                    if pedestrian_far_speed
                    else "pedestrian_speed_outlier"
                    if pedestrian_outlier
                    else "class_speed_limit"
                    if fused_speed_kmh > motion_profile.max_speed_kmh
                    else "uncertainty_gate"
                ),
                speed_confidence=speed_confidence,
                speed_uncertainty_kmh=uncertainty.speed_uncertainty_kmh,
                window_residual_m=regression.residual_m,
                position_rmse_m=effective_position_rmse_m,
                position_sigma_m=local_uncertainty.position_sigma_m,
                position_covariance=position_covariance,
                measurement_source=measurement_source,
                measurement_confidence=bounded_measurement_confidence,
                local_scale_factor=local_uncertainty.local_scale_factor,
                local_scale_percentile=local_scale_percentile,
                plane_id=plane_id,
                contact_source=measurement_source,
                world_position_covariance=position_covariance,
                speed_geometry_diagnostics=speed_geometry_diagnostics,
                adaptive_measurement_noise_multiplier=adaptive_state.multiplier,
                innovation_nis=innovation_nis,
                perspective_result=perspective_result,
                pedestrian_result=pedestrian_result,
            )
            return None

        history.auxiliary_velocity_weight = auxiliary_weight
        history.speeds_kmh.append(fused_speed_kmh)
        median_speed = median_smoothing(history.speeds_kmh, self.smoothing_window)
        smoothed_speed = self._stabilize_display_speed(
            history,
            median_speed,
            timestamp_sec,
            motion_profile,
        )
        previous_record = self._latest_records.get(tracker_id)
        acceleration_mps2 = self._acceleration_mps2(
            previous_record,
            smoothed_speed,
            timestamp_sec,
        )
        display_velocity_mps = self._scaled_velocity(
            fused_velocity_mps,
            fused_speed_kmh,
            smoothed_speed,
        )
        self._latest_records[tracker_id] = SpeedRecord(
            tracker_id=tracker_id,
            speed_kmh=smoothed_speed,
            timestamp_sec=timestamp_sec,
            world_x=world_position[0],
            world_y=world_position[1],
            speed_uncertainty_kmh=uncertainty.speed_uncertainty_kmh,
            speed_confidence=speed_confidence,
            position_rmse_m=uncertainty.position_rmse_m,
            position_sigma_m=local_uncertainty.position_sigma_m,
            position_covariance=position_covariance,
            measurement_source=measurement_source,
            measurement_confidence=bounded_measurement_confidence,
            local_scale_factor=local_uncertainty.local_scale_factor,
            local_scale_percentile=local_scale_percentile,
            adaptive_measurement_noise_multiplier=adaptive_state.multiplier,
            innovation_nis=innovation_nis,
            velocity_x_mps=display_velocity_mps[0],
            velocity_y_mps=display_velocity_mps[1],
            heading_deg=self._heading_deg(display_velocity_mps),
            acceleration_mps2=acceleration_mps2,
            physics_valid=True,
            quality_label="stable",
            rejection_reason=None,
            track_age_frames=track_age,
            window_residual_m=regression.residual_m,
            perspective_speed_inflation_detected=(
                perspective_result.perspective_speed_inflation_detected
            ),
            speed_scale_correlation=perspective_result.speed_scale_correlation,
            far_near_speed_ratio=perspective_result.far_near_speed_ratio,
            geometry_rejection_reason=perspective_result.geometry_rejection_reason,
            pedestrian_scale_drift_detected=pedestrian_result.scale_drift_detected,
            speed_inverse_height_correlation=(
                pedestrian_result.speed_inverse_height_correlation
            ),
            height_consistency_score=pedestrian_result.height_consistency_score,
            recommended_speed_scale_factor=(
                pedestrian_result.recommended_speed_scale_factor
            ),
            pedestrian_geometry_model_reference=pedestrian_result.model_reference,
            plane_id=plane_id,
            contact_source=measurement_source,
            world_position_covariance=position_covariance,
            speed_geometry_diagnostics=speed_geometry_diagnostics,
        )
        return smoothed_speed

    def _legacy_update(
        self,
        tracker_id: int,
        pixel_center: tuple[float, float],
        timestamp_sec: float,
        process_noise: str | None = None,
    ) -> float | None:
        world_position = self.view_transformer.transform_point(*pixel_center)
        history = self._histories.setdefault(tracker_id, TrackHistory(tracker_id))
        previous_position = history.last_position
        previous_timestamp = history.last_timestamp
        history.add_position(world_position, timestamp_sec)

        if previous_position is None or previous_timestamp is None:
            if process_noise is not None:
                self._kalman_filters.setdefault(
                    tracker_id,
                    KalmanFilter2D(kalman_config_for_motion_profile(process_noise)),
                ).update(world_position, timestamp_sec)
            return None

        delta_t = timestamp_sec - previous_timestamp
        if delta_t <= 0:
            return None

        displacement = math.dist(previous_position, world_position)
        measured_velocity = (
            (world_position[0] - previous_position[0]) / delta_t,
            (world_position[1] - previous_position[1]) / delta_t,
        )
        uncertainty = estimate_speed_uncertainty(
            displacement_m=displacement,
            delta_t_sec=delta_t,
            position_rmse_m=self.position_rmse_m,
            timestamp_uncertainty_sec=self.timestamp_uncertainty_sec,
        )
        filtered_displacement = min_displacement_filter(displacement, self.min_displacement_m)
        if filtered_displacement == 0.0:
            speed_kmh = 0.0
            velocity_mps = (0.0, 0.0)
        elif process_noise is not None:
            kalman_state = self._kalman_filters.setdefault(
                tracker_id,
                KalmanFilter2D(kalman_config_for_motion_profile(process_noise)),
            ).update(world_position, timestamp_sec)
            speed_kmh = kalman_state.speed_kmh
            velocity_mps = kalman_state.velocity_mps
            uncertainty = estimate_speed_uncertainty(
                displacement_m=max(displacement, filtered_displacement),
                delta_t_sec=delta_t,
                position_rmse_m=self.position_rmse_m,
                timestamp_uncertainty_sec=self.timestamp_uncertainty_sec,
            )
        else:
            speed_kmh = (filtered_displacement / delta_t) * 3.6
            velocity_mps = measured_velocity

        filtered_speed_kmh = max_speed_filter(speed_kmh, self.max_speed_kmh)
        if filtered_speed_kmh is None:
            return None

        previous_speed_kmh = history.speeds_kmh[-1] if history.speeds_kmh else None
        history.speeds_kmh.append(filtered_speed_kmh)
        smoothed_speed = median_smoothing(history.speeds_kmh, self.smoothing_window)
        acceleration_mps2 = (
            ((filtered_speed_kmh - previous_speed_kmh) / 3.6) / delta_t
            if previous_speed_kmh is not None
            else None
        )
        self._latest_records[tracker_id] = SpeedRecord(
            tracker_id=tracker_id,
            speed_kmh=smoothed_speed,
            timestamp_sec=timestamp_sec,
            world_x=world_position[0],
            world_y=world_position[1],
            speed_uncertainty_kmh=uncertainty.speed_uncertainty_kmh,
            speed_confidence=uncertainty.speed_confidence,
            position_rmse_m=uncertainty.position_rmse_m,
            velocity_x_mps=velocity_mps[0],
            velocity_y_mps=velocity_mps[1],
            heading_deg=self._heading_deg(velocity_mps),
            acceleration_mps2=acceleration_mps2,
            physics_valid=True,
            quality_label="stable",
            rejection_reason=None,
            track_age_frames=len(history.positions),
            window_residual_m=None,
        )
        return smoothed_speed

    def get_record(self, tracker_id: int) -> SpeedRecord | None:
        return self._latest_records.get(tracker_id)

    def get_all_records(self) -> dict[int, SpeedRecord]:
        return dict(self._latest_records)

    def get_speed(self, tracker_id: int) -> float | None:
        record = self._latest_records.get(tracker_id)
        return record.speed_kmh if record is not None else None

    def get_all_speeds(self) -> dict[int, float]:
        return {
            tracker_id: record.speed_kmh
            for tracker_id, record in self._latest_records.items()
            if record.speed_kmh is not None
        }

    def annotate_record(self, tracker_id: int, **fields: object) -> None:
        record = self._latest_records.get(tracker_id)
        if record is None:
            return
        self._latest_records[tracker_id] = replace(record, **cast(Any, fields))

    def suppress_measurement(
        self,
        *,
        tracker_id: int,
        pixel_point: tuple[float, float],
        timestamp_sec: float,
        quality_label: str,
        rejection_reason: str,
        preserve_previous_speed: bool = False,
        measurement_source: str | None = None,
        measurement_confidence: float | None = None,
        local_scale_percentile: float | None = None,
        bev_risk_level: str | None = None,
        bev_risk_reason: str | None = None,
        scale_confidence_label: str | None = None,
        weak_calibration_reason: str | None = None,
        plane_id: str | None = None,
        speed_geometry_diagnostics: dict[str, object] | None = None,
    ) -> SpeedRecord:
        world_position = self.view_transformer.transform_point(*pixel_point)
        previous = self._latest_records.get(tracker_id)
        keep_previous = (
            preserve_previous_speed
            and previous is not None
            and previous.physics_valid
            and previous.speed_kmh is not None
        )
        record = SpeedRecord(
            tracker_id=tracker_id,
            speed_kmh=previous.speed_kmh if keep_previous and previous is not None else None,
            timestamp_sec=timestamp_sec,
            world_x=world_position[0],
            world_y=world_position[1],
            speed_uncertainty_kmh=(
                previous.speed_uncertainty_kmh
                if keep_previous and previous is not None
                else None
            ),
            speed_confidence=(
                previous.speed_confidence if keep_previous and previous is not None else None
            ),
            position_rmse_m=self.position_rmse_m,
            velocity_x_mps=(
                previous.velocity_x_mps if keep_previous and previous is not None else None
            ),
            velocity_y_mps=(
                previous.velocity_y_mps if keep_previous and previous is not None else None
            ),
            heading_deg=previous.heading_deg if keep_previous and previous is not None else None,
            physics_valid=False,
            quality_label=quality_label,
            rejection_reason=rejection_reason,
            track_age_frames=(
                len(self._histories[tracker_id].positions)
                if tracker_id in self._histories
                else 0
            ),
            measurement_source=measurement_source,
            measurement_confidence=measurement_confidence,
            local_scale_percentile=local_scale_percentile,
            bev_risk_level=bev_risk_level,
            bev_risk_reason=bev_risk_reason,
            speed_frozen=bool(keep_previous),
            scale_confidence_label=scale_confidence_label,
            weak_calibration_reason=weak_calibration_reason,
            geometry_rejection_reason=rejection_reason,
            plane_id=plane_id,
            contact_source=measurement_source,
            speed_geometry_diagnostics=speed_geometry_diagnostics,
        )
        self._latest_records[tracker_id] = record
        return record

    def reset_track(self, tracker_id: int) -> None:
        self._histories.pop(tracker_id, None)
        self._latest_records.pop(tracker_id, None)
        self._kalman_filters.pop(tracker_id, None)
        self._adaptive_noise_controllers.pop(tracker_id, None)
        self._perspective_samples.pop(tracker_id, None)
        self._pedestrian_geometry_samples.pop(tracker_id, None)

    def reset(self) -> None:
        self._histories.clear()
        self._latest_records.clear()
        self._kalman_filters.clear()
        self._adaptive_noise_controllers.clear()
        self._perspective_samples.clear()
        self._pedestrian_geometry_samples.clear()

    def _quality_record(
        self,
        *,
        tracker_id: int,
        timestamp_sec: float,
        world_position: tuple[float, float],
        motion_profile: MotionProfile,
        quality_label: str,
        rejection_reason: str | None,
        speed_confidence: float | None = None,
        speed_uncertainty_kmh: float | None = None,
        window_residual_m: float | None = None,
        position_rmse_m: float | None = None,
        position_sigma_m: float | None = None,
        position_covariance: list[list[float]] | None = None,
        measurement_source: str | None = None,
        measurement_confidence: float | None = None,
        local_scale_factor: float | None = None,
        local_scale_percentile: float | None = None,
        plane_id: str | None = None,
        contact_source: str | None = None,
        world_position_covariance: list[list[float]] | None = None,
        speed_geometry_diagnostics: dict[str, object] | None = None,
        adaptive_measurement_noise_multiplier: float | None = None,
        innovation_nis: float | None = None,
        perspective_result: PerspectiveGuardResult | None = None,
        pedestrian_result: PedestrianScaleDriftResult | None = None,
    ) -> SpeedRecord:
        history = self._histories.get(tracker_id)
        perspective_result = perspective_result or PerspectiveGuardResult(
            False,
            None,
            None,
            None,
        )
        pedestrian_result = pedestrian_result or PedestrianScaleDriftResult(
            False,
            None,
            None,
            None,
            0.0,
            None,
            None,
        )
        return SpeedRecord(
            tracker_id=tracker_id,
            speed_kmh=None,
            timestamp_sec=timestamp_sec,
            world_x=world_position[0],
            world_y=world_position[1],
            speed_uncertainty_kmh=speed_uncertainty_kmh,
            speed_confidence=speed_confidence,
            position_rmse_m=(
                position_rmse_m if position_rmse_m is not None else self.position_rmse_m
            ),
            position_sigma_m=position_sigma_m,
            position_covariance=position_covariance,
            measurement_source=measurement_source,
            measurement_confidence=measurement_confidence,
            local_scale_factor=local_scale_factor,
            local_scale_percentile=local_scale_percentile,
            plane_id=plane_id,
            contact_source=contact_source,
            world_position_covariance=world_position_covariance,
            speed_geometry_diagnostics=speed_geometry_diagnostics,
            adaptive_measurement_noise_multiplier=adaptive_measurement_noise_multiplier,
            innovation_nis=innovation_nis,
            perspective_speed_inflation_detected=(
                perspective_result.perspective_speed_inflation_detected
            ),
            speed_scale_correlation=perspective_result.speed_scale_correlation,
            far_near_speed_ratio=perspective_result.far_near_speed_ratio,
            geometry_rejection_reason=perspective_result.geometry_rejection_reason,
            pedestrian_scale_drift_detected=pedestrian_result.scale_drift_detected,
            speed_inverse_height_correlation=(
                pedestrian_result.speed_inverse_height_correlation
            ),
            height_consistency_score=pedestrian_result.height_consistency_score,
            recommended_speed_scale_factor=(
                pedestrian_result.recommended_speed_scale_factor
            ),
            pedestrian_geometry_model_reference=pedestrian_result.model_reference,
            velocity_x_mps=None,
            velocity_y_mps=None,
            heading_deg=None,
            acceleration_mps2=None,
            physics_valid=False,
            quality_label=quality_label,
            rejection_reason=rejection_reason,
            track_age_frames=len(history.positions) if history is not None else 0,
            window_residual_m=window_residual_m,
        )

    @staticmethod
    def _hard_speed_rejection_reason(motion_profile: MotionProfile) -> str:
        if motion_profile.category == "low_inertia_dynamic":
            return "pedestrian_physical_speed_gate"
        return "speed_gate"

    def _instant_perspective_result(
        self,
        speed_kmh: float,
        local_scale_percentile: float | None,
        motion_profile: MotionProfile,
    ) -> PerspectiveGuardResult:
        if (
            motion_profile.category == "low_inertia_dynamic"
            and (local_scale_percentile or 0.0) >= 0.85
            and speed_kmh > motion_profile.max_speed_kmh
        ):
            return PerspectiveGuardResult(
                True,
                None,
                None,
                "perspective_speed_inflation",
            )
        return PerspectiveGuardResult(False, None, None, None)

    def _update_perspective_guard(
        self,
        *,
        tracker_id: int,
        speed_kmh: float,
        pixel_y: float,
        local_scale_factor: float,
        local_scale_percentile: float | None,
        timestamp_sec: float,
        motion_profile: MotionProfile,
    ) -> PerspectiveGuardResult:
        percentile = (
            float(local_scale_percentile)
            if local_scale_percentile is not None
            else min(1.0, max(0.0, local_scale_factor / 8.0))
        )
        samples = self._perspective_samples.setdefault(tracker_id, [])
        samples.append(
            PerspectiveGuardSample(
                speed_kmh=float(speed_kmh),
                pixel_y=float(pixel_y),
                local_scale_factor=float(local_scale_factor),
                local_scale_percentile=percentile,
                timestamp_sec=float(timestamp_sec),
            )
        )
        if len(samples) > 12:
            del samples[:-12]
        return self._perspective_guard.analyze(
            samples,
            max_speed_kmh=motion_profile.max_speed_kmh,
        )

    def _update_pedestrian_scale_drift(
        self,
        *,
        tracker_id: int,
        speed_kmh: float,
        pixel_center: tuple[float, float],
        local_scale_factor: float,
        local_scale_percentile: float | None,
        motion_profile: MotionProfile,
        timestamp_sec: float,
        bbox_xyxy: list[float] | None,
        bbox_height_px: float | None,
        pose_ankle_pixel: tuple[float, float] | None,
        pose_head_pixel: tuple[float, float] | None,
    ) -> PedestrianScaleDriftResult:
        empty = PedestrianScaleDriftResult(False, None, None, None, 0.0, None, None)
        if motion_profile.category != "low_inertia_dynamic" or bbox_xyxy is None:
            return empty
        if len(bbox_xyxy) != 4:
            return empty
        x1, y1, x2, y2 = [float(value) for value in bbox_xyxy]
        height = (
            float(bbox_height_px)
            if bbox_height_px is not None
            else max(y2 - y1, 1.0)
        )
        if height <= 0.0:
            return empty
        bbox_top = ((x1 + x2) / 2.0, y1)
        bbox_bottom = ((x1 + x2) / 2.0, y2)
        percentile = (
            float(local_scale_percentile)
            if local_scale_percentile is not None
            else min(1.0, max(0.0, local_scale_factor / 8.0))
        )
        samples = self._pedestrian_geometry_samples.setdefault(tracker_id, [])
        samples.append(
            PedestrianGeometrySample(
                tracker_id=tracker_id,
                speed_kmh=float(speed_kmh),
                bbox_top=bbox_top,
                bbox_bottom=bbox_bottom,
                bbox_height_px=height,
                footpoint_pixel=pixel_center,
                pixel_y=float(pixel_center[1]),
                local_scale_factor=float(local_scale_factor),
                local_scale_percentile=percentile,
                timestamp_sec=float(timestamp_sec),
                pose_ankle_pixel=pose_ankle_pixel,
                pose_head_pixel=pose_head_pixel,
            )
        )
        if len(samples) > 12:
            del samples[:-12]
        return self._pedestrian_scale_drift.analyze(samples)

    def _measurement_covariance(
        self,
        pixel_center: tuple[float, float],
        local_uncertainty: LocalPositionUncertainty,
        scalar_measurement_noise: float,
        pixel_covariance_px: list[list[float]] | None,
    ) -> NDArray[np.float64]:
        fallback = np.eye(2, dtype=np.float64) * max(float(scalar_measurement_noise), 1e-6)
        try:
            covariance = np.asarray(local_uncertainty.covariance, dtype=np.float64)
            if covariance.shape != (2, 2):
                covariance = fallback.copy()
            else:
                covariance = covariance.copy()
            if pixel_covariance_px is not None:
                pixel_covariance = np.asarray(pixel_covariance_px, dtype=np.float64)
                if pixel_covariance.shape == (2, 2):
                    pixel_covariance = (pixel_covariance + pixel_covariance.T) * 0.5
                    jacobian = self.view_transformer.local_jacobian(
                        pixel_center[0],
                        pixel_center[1],
                    )
                    covariance += jacobian @ pixel_covariance @ jacobian.T
            covariance = (covariance + covariance.T) * 0.5
            covariance[0, 0] = max(float(covariance[0, 0]), scalar_measurement_noise)
            covariance[1, 1] = max(float(covariance[1, 1]), scalar_measurement_noise)
            min_eigenvalue = float(np.min(np.linalg.eigvalsh(covariance)))
            if min_eigenvalue < 1e-9:
                covariance += np.eye(2, dtype=np.float64) * (1e-9 - min_eigenvalue)
            return covariance.astype(np.float64)
        except (TypeError, ValueError, np.linalg.LinAlgError):
            return fallback

    @staticmethod
    def _fit_window(
        history: TrackHistory,
        regression_window_sec: float,
    ) -> _RegressionState | None:
        if len(history.positions) < 2:
            return None
        latest_timestamp = history.timestamps[-1]
        window_start = latest_timestamp - regression_window_sec
        samples: list[tuple[float, tuple[float, float], float, float, float | None]] = []
        has_quality = (
            len(history.measurement_confidences) == len(history.timestamps)
            and len(history.position_sigmas_m) == len(history.timestamps)
        )
        has_scale_percentiles = len(history.local_scale_percentiles) == len(
            history.timestamps,
        )
        for index, (timestamp, position) in enumerate(
            zip(history.timestamps, history.positions, strict=True)
        ):
            if timestamp < window_start:
                continue
            confidence = history.measurement_confidences[index] if has_quality else 1.0
            sigma = history.position_sigmas_m[index] if has_quality else 0.0
            scale_percentile = (
                history.local_scale_percentiles[index] if has_scale_percentiles else None
            )
            samples.append((timestamp, position, confidence, sigma, scale_percentile))
        if len(samples) < 3:
            return None
        timestamps = [timestamp for timestamp, _, _, _, _ in samples]
        duration_sec = timestamps[-1] - timestamps[0]
        if duration_sec < 0.25:
            return None
        xs = [position[0] for _, position, _, _, _ in samples]
        ys = [position[1] for _, position, _, _, _ in samples]
        base_weights = [
            (
                max(0.05, min(1.0, confidence))
                / (1.0 + max(0.0, sigma))
                * SpeedEstimator._perspective_regression_weight(scale_percentile)
            )
            for _, _, confidence, sigma, scale_percentile in samples
        ]
        base_weight_sum = max(sum(base_weights), 1e-9)
        mean_t = (
            sum(
                weight * timestamp
                for weight, timestamp in zip(base_weights, timestamps, strict=True)
            )
            / base_weight_sum
        )
        centered_t = [timestamp - mean_t for timestamp in timestamps]
        denominator = sum(
            weight * value * value
            for weight, value in zip(base_weights, centered_t, strict=True)
        )
        if denominator <= 1e-9:
            return None
        mean_x, vx = SpeedEstimator._weighted_line_fit(centered_t, xs, base_weights)
        mean_y, vy = SpeedEstimator._weighted_line_fit(centered_t, ys, base_weights)
        residuals = [
            math.dist(
                (x, y),
                (mean_x + vx * dt, mean_y + vy * dt),
            )
            for dt, x, y in zip(centered_t, xs, ys, strict=True)
        ]
        huber_scale = max(0.15, sorted(residuals)[len(residuals) // 2] * 1.4826)
        robust_weights = [
            weight * min(1.0, huber_scale / max(residual, 1e-9))
            for weight, residual in zip(base_weights, residuals, strict=True)
        ]
        mean_x, vx = SpeedEstimator._weighted_line_fit(centered_t, xs, robust_weights)
        mean_y, vy = SpeedEstimator._weighted_line_fit(centered_t, ys, robust_weights)
        residuals = [
            math.dist(
                (x, y),
                (mean_x + vx * dt, mean_y + vy * dt),
            )
            for dt, x, y in zip(centered_t, xs, ys, strict=True)
        ]
        weight_sum = max(sum(robust_weights), 1e-9)
        residual_m = (
            sum(
                weight * value * value
                for weight, value in zip(robust_weights, residuals, strict=True)
            )
            / weight_sum
        ) ** 0.5
        speed_mps = (vx**2 + vy**2) ** 0.5
        return _RegressionState(
            velocity_mps=(float(vx), float(vy)),
            speed_kmh=float(speed_mps * 3.6),
            duration_sec=float(duration_sec),
            displacement_m=float(speed_mps * duration_sec),
            residual_m=float(residual_m),
        )

    @staticmethod
    def _perspective_regression_weight(local_scale_percentile: float | None) -> float:
        if local_scale_percentile is None:
            return 1.0
        percentile = max(0.0, min(1.0, float(local_scale_percentile)))
        if percentile <= 0.75:
            return 1.0
        return max(0.05, 1.0 / (1.0 + ((percentile - 0.75) * 10.0) ** 2))

    @staticmethod
    def _weighted_line_fit(
        centered_t: list[float],
        values: list[float],
        weights: list[float],
    ) -> tuple[float, float]:
        weight_sum = max(sum(weights), 1e-9)
        intercept = (
            sum(weight * value for weight, value in zip(weights, values, strict=True))
            / weight_sum
        )
        denominator = sum(
            weight * dt * dt for weight, dt in zip(weights, centered_t, strict=True)
        )
        if denominator <= 1e-9:
            return float(intercept), 0.0
        slope = sum(
            weight * dt * (value - intercept)
            for weight, dt, value in zip(weights, centered_t, values, strict=True)
        ) / denominator
        return float(intercept), float(slope)

    @staticmethod
    def _acceleration_mps2(
        previous_record: SpeedRecord | None,
        current_speed_kmh: float,
        timestamp_sec: float,
    ) -> float | None:
        if previous_record is None or previous_record.speed_kmh is None:
            return None
        delta_t = timestamp_sec - previous_record.timestamp_sec
        if delta_t <= 0:
            return None
        return ((current_speed_kmh - previous_record.speed_kmh) / 3.6) / delta_t

    @staticmethod
    def _stabilize_display_speed(
        history: TrackHistory,
        candidate_speed_kmh: float,
        timestamp_sec: float,
        motion_profile: MotionProfile,
    ) -> float:
        previous_speed = history.displayed_speed_kmh
        previous_timestamp = history.displayed_timestamp_sec
        if previous_speed is None or previous_timestamp is None:
            history.displayed_speed_kmh = candidate_speed_kmh
            history.displayed_timestamp_sec = timestamp_sec
            return candidate_speed_kmh

        delta_t = max(timestamp_sec - previous_timestamp, 1e-3)
        max_step_kmh = max(
            0.35,
            motion_profile.max_acceleration_mps2 * delta_t * 3.6,
        )
        max_step_kmh = min(max_step_kmh, SpeedEstimator._display_step_cap_kmh(motion_profile))
        lower = previous_speed - max_step_kmh
        upper = previous_speed + max_step_kmh
        stabilized_speed = min(max(candidate_speed_kmh, lower), upper)
        history.displayed_speed_kmh = stabilized_speed
        history.displayed_timestamp_sec = timestamp_sec
        return stabilized_speed

    @staticmethod
    def _scaled_velocity(
        velocity_mps: tuple[float, float],
        source_speed_kmh: float,
        target_speed_kmh: float,
    ) -> tuple[float, float]:
        if source_speed_kmh <= 1e-9:
            return (0.0, 0.0)
        scale = target_speed_kmh / source_speed_kmh
        return (float(velocity_mps[0] * scale), float(velocity_mps[1] * scale))

    @staticmethod
    def _fuse_velocity(
        regression_velocity_mps: tuple[float, float],
        auxiliary_velocity_mps: tuple[float, float] | None,
        auxiliary_confidence: float,
        residual_m: float,
        motion_profile: MotionProfile,
    ) -> tuple[tuple[float, float], float]:
        if auxiliary_velocity_mps is None or auxiliary_confidence <= 0.0:
            return regression_velocity_mps, 0.0
        regression_speed = SpeedEstimator._speed_kmh(regression_velocity_mps)
        auxiliary_speed = SpeedEstimator._speed_kmh(auxiliary_velocity_mps)
        if regression_speed <= 1e-6 or auxiliary_speed <= 1e-6:
            return regression_velocity_mps, 0.0
        angle_deg = SpeedEstimator._velocity_angle_deg(
            regression_velocity_mps,
            auxiliary_velocity_mps,
        )
        if angle_deg > 25.0:
            return regression_velocity_mps, 0.0
        relative_delta = abs(auxiliary_speed - regression_speed) / max(regression_speed, 1.0)
        if relative_delta > 0.30:
            return regression_velocity_mps, 0.0
        residual_weight = min(0.2, max(0.0, residual_m) * 0.12)
        weight_cap = SpeedEstimator._auxiliary_weight_cap(motion_profile)
        weight = min(
            weight_cap,
            max(0.0, min(1.0, auxiliary_confidence)) * weight_cap + residual_weight,
        )
        return (
            (
                regression_velocity_mps[0] * (1.0 - weight) + auxiliary_velocity_mps[0] * weight,
                regression_velocity_mps[1] * (1.0 - weight) + auxiliary_velocity_mps[1] * weight,
            ),
            float(weight),
        )

    @staticmethod
    def _speed_kmh(velocity_mps: tuple[float, float]) -> float:
        return float(((velocity_mps[0] ** 2 + velocity_mps[1] ** 2) ** 0.5) * 3.6)

    @staticmethod
    def _velocity_angle_deg(
        left: tuple[float, float],
        right: tuple[float, float],
    ) -> float:
        left_norm = (left[0] ** 2 + left[1] ** 2) ** 0.5
        right_norm = (right[0] ** 2 + right[1] ** 2) ** 0.5
        if left_norm <= 1e-9 or right_norm <= 1e-9:
            return 180.0
        cosine = (left[0] * right[0] + left[1] * right[1]) / (left_norm * right_norm)
        cosine = max(-1.0, min(1.0, cosine))
        return float(math.degrees(math.acos(cosine)))

    @staticmethod
    def _auxiliary_weight_cap(motion_profile: MotionProfile) -> float:
        if motion_profile.category in {"high_inertia_dynamic", "heavy_vehicle_dynamic"}:
            return 0.35
        if motion_profile.category == "bicycle_dynamic":
            return 0.25
        if motion_profile.category == "low_inertia_dynamic":
            return 0.20
        return 0.25

    @staticmethod
    def _display_step_cap_kmh(motion_profile: MotionProfile) -> float:
        if motion_profile.category in {"high_inertia_dynamic", "heavy_vehicle_dynamic"}:
            return 1.5
        if motion_profile.category == "motorcycle_dynamic":
            return 1.2
        if motion_profile.category == "bicycle_dynamic":
            return 0.9
        if motion_profile.category == "low_inertia_dynamic":
            return 0.58
        return 0.8

    @staticmethod
    def _heading_deg(velocity_mps: tuple[float, float]) -> float | None:
        vx, vy = velocity_mps
        if abs(vx) < 1e-9 and abs(vy) < 1e-9:
            return None
        return float((math.degrees(math.atan2(vy, vx)) + 360.0) % 360.0)
