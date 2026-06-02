from __future__ import annotations

import math
from dataclasses import dataclass

from shared.configs.constants import DEFAULT_MAX_SPEED_KMH, DEFAULT_MIN_DISPLACEMENT_M

from domain.motion.models import MotionProfile
from domain.speed.filters import max_speed_filter, min_displacement_filter
from domain.speed.kalman import KalmanFilter2D, kalman_config_for_motion_profile
from domain.speed.models import SpeedRecord, TrackHistory
from domain.speed.smoothing import median_smoothing
from domain.speed.uncertainty import estimate_speed_uncertainty
from domain.speed.view_transformer import ViewTransformer

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
        self._kalman_filters: dict[int, KalmanFilter2D] = {}

    def update(
        self,
        tracker_id: int,
        pixel_center: tuple[float, float],
        timestamp_sec: float,
        process_noise: str | None = None,
        motion_profile: MotionProfile | None = None,
        detection_confidence: float = 1.0,
        auxiliary_velocity_mps: tuple[float, float] | None = None,
        auxiliary_confidence: float = 0.0,
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
        history = self._histories.setdefault(tracker_id, TrackHistory(tracker_id))
        previous_position = history.last_position
        previous_timestamp = history.last_timestamp

        if previous_position is None or previous_timestamp is None:
            history.add_position(world_position, timestamp_sec)
            self._kalman_filters.setdefault(
                tracker_id,
                KalmanFilter2D(kalman_config_for_motion_profile(motion_profile.process_noise)),
            ).update(world_position, timestamp_sec)
            self._latest_records[tracker_id] = self._quality_record(
                tracker_id=tracker_id,
                timestamp_sec=timestamp_sec,
                world_position=world_position,
                motion_profile=motion_profile,
                quality_label="warming_up",
                rejection_reason=None,
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
            self._latest_records[tracker_id] = self._quality_record(
                tracker_id=tracker_id,
                timestamp_sec=timestamp_sec,
                world_position=world_position,
                motion_profile=motion_profile,
                quality_label="rejected",
                rejection_reason="speed_gate",
            )
            return None

        kalman_filter = self._kalman_filters.setdefault(
            tracker_id,
            KalmanFilter2D(kalman_config_for_motion_profile(motion_profile.process_noise)),
        )
        predicted_measurement = kalman_filter.predict_measurement(world_position, timestamp_sec)
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
            )
            return None

        history.add_position(world_position, timestamp_sec)
        kalman_state = kalman_filter.update(world_position, timestamp_sec)
        track_age = len(history.positions)
        if track_age < motion_profile.min_track_age_frames:
            self._latest_records[tracker_id] = self._quality_record(
                tracker_id=tracker_id,
                timestamp_sec=timestamp_sec,
                world_position=world_position,
                motion_profile=motion_profile,
                quality_label="warming_up",
                rejection_reason=None,
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
            )
            return None

        fused_velocity_mps, auxiliary_weight = self._fuse_velocity(
            regression.velocity_mps,
            auxiliary_velocity_mps,
            auxiliary_confidence,
            regression.residual_m,
        )
        fused_speed_kmh = self._speed_kmh(fused_velocity_mps)
        if fused_speed_kmh > hard_max_speed:
            history.rejected_observations += 1
            self._latest_records[tracker_id] = self._quality_record(
                tracker_id=tracker_id,
                timestamp_sec=timestamp_sec,
                world_position=world_position,
                motion_profile=motion_profile,
                quality_label="rejected",
                rejection_reason="speed_gate",
                window_residual_m=regression.residual_m,
            )
            return None

        uncertainty_cap = max(8.0, motion_profile.max_speed_kmh * 0.35)
        uncertainty = estimate_speed_uncertainty(
            displacement_m=max((fused_speed_kmh / 3.6) * regression.duration_sec, 1e-6),
            delta_t_sec=regression.duration_sec,
            position_rmse_m=self.position_rmse_m,
            timestamp_uncertainty_sec=self.timestamp_uncertainty_sec,
            residual_m=regression.residual_m,
            detection_confidence=min(1.0, detection_confidence + auxiliary_weight * 0.2),
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
            self._latest_records[tracker_id] = self._quality_record(
                tracker_id=tracker_id,
                timestamp_sec=timestamp_sec,
                world_position=world_position,
                motion_profile=motion_profile,
                quality_label="low_confidence",
                rejection_reason=(
                    "class_speed_limit"
                    if fused_speed_kmh > motion_profile.max_speed_kmh
                    else "uncertainty_gate"
                ),
                speed_confidence=speed_confidence,
                speed_uncertainty_kmh=uncertainty.speed_uncertainty_kmh,
                window_residual_m=regression.residual_m,
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
            velocity_x_mps=display_velocity_mps[0],
            velocity_y_mps=display_velocity_mps[1],
            heading_deg=self._heading_deg(display_velocity_mps),
            acceleration_mps2=acceleration_mps2,
            physics_valid=True,
            quality_label="stable",
            rejection_reason=None,
            track_age_frames=track_age,
            window_residual_m=regression.residual_m,
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

    def reset(self) -> None:
        self._histories.clear()
        self._latest_records.clear()
        self._kalman_filters.clear()

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
    ) -> SpeedRecord:
        history = self._histories.get(tracker_id)
        return SpeedRecord(
            tracker_id=tracker_id,
            speed_kmh=None,
            timestamp_sec=timestamp_sec,
            world_x=world_position[0],
            world_y=world_position[1],
            speed_uncertainty_kmh=speed_uncertainty_kmh,
            speed_confidence=speed_confidence,
            position_rmse_m=self.position_rmse_m,
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
    def _fit_window(
        history: TrackHistory,
        regression_window_sec: float,
    ) -> _RegressionState | None:
        if len(history.positions) < 2:
            return None
        latest_timestamp = history.timestamps[-1]
        window_start = latest_timestamp - regression_window_sec
        samples = [
            (timestamp, position)
            for timestamp, position in zip(history.timestamps, history.positions, strict=True)
            if timestamp >= window_start
        ]
        if len(samples) < 3:
            return None
        timestamps = [timestamp for timestamp, _ in samples]
        duration_sec = timestamps[-1] - timestamps[0]
        if duration_sec < 0.25:
            return None
        mean_t = sum(timestamps) / len(timestamps)
        centered_t = [timestamp - mean_t for timestamp in timestamps]
        denominator = sum(value * value for value in centered_t)
        if denominator <= 1e-9:
            return None
        xs = [position[0] for _, position in samples]
        ys = [position[1] for _, position in samples]
        mean_x = sum(xs) / len(xs)
        mean_y = sum(ys) / len(ys)
        vx = sum(dt * (x - mean_x) for dt, x in zip(centered_t, xs, strict=True)) / denominator
        vy = sum(dt * (y - mean_y) for dt, y in zip(centered_t, ys, strict=True)) / denominator
        residuals = [
            math.dist(
                (x, y),
                (mean_x + vx * dt, mean_y + vy * dt),
            )
            for dt, x, y in zip(centered_t, xs, ys, strict=True)
        ]
        residual_m = (sum(value * value for value in residuals) / len(residuals)) ** 0.5
        speed_mps = (vx**2 + vy**2) ** 0.5
        return _RegressionState(
            velocity_mps=(float(vx), float(vy)),
            speed_kmh=float(speed_mps * 3.6),
            duration_sec=float(duration_sec),
            displacement_m=float(speed_mps * duration_sec),
            residual_m=float(residual_m),
        )

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
    ) -> tuple[tuple[float, float], float]:
        if auxiliary_velocity_mps is None or auxiliary_confidence <= 0.0:
            return regression_velocity_mps, 0.0
        auxiliary_speed = SpeedEstimator._speed_kmh(auxiliary_velocity_mps)
        if auxiliary_speed <= 1e-6:
            return regression_velocity_mps, 0.0
        residual_weight = min(0.2, max(0.0, residual_m) * 0.12)
        weight = min(0.92, max(0.0, min(1.0, auxiliary_confidence)) * 0.82 + residual_weight)
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
    def _heading_deg(velocity_mps: tuple[float, float]) -> float | None:
        vx, vy = velocity_mps
        if abs(vx) < 1e-9 and abs(vy) < 1e-9:
            return None
        return float((math.degrees(math.atan2(vy, vx)) + 360.0) % 360.0)
