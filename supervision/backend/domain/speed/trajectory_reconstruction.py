from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np

from domain.motion.router import MotionRouter
from domain.speed.stability import SpeedStabilityMetrics, compute_speed_stability


@dataclass(frozen=True)
class TrajectoryPoint:
    report_index: int
    timestamp_sec: float
    world_x: float
    world_y: float
    raw_speed_kmh: float | None
    reconstructed: bool = False


class TrajectoryReconstructor:
    def __init__(self, motion_router: MotionRouter | None = None) -> None:
        self.motion_router = motion_router or MotionRouter()

    def reconstruct_reports(self, frame_reports: list[dict[str, Any]]) -> list[dict[str, Any]]:
        grouped = self._group_points(frame_reports)
        updated_reports = [self._copy_report(report) for report in frame_reports]
        for tracker_id, points in grouped.items():
            if not points:
                continue
            class_id = self._class_id_for_track(frame_reports, tracker_id)
            if class_id is None:
                continue
            profile = self.motion_router.route_class(class_id)
            if not profile.should_estimate_speed:
                continue
            track_points = self._fill_short_gaps(frame_reports, points)
            reconstructed = self.reconstruct_track(track_points, class_id)
            self._apply_track(updated_reports, tracker_id, class_id, reconstructed)
        diagnostics = self._trajectory_diagnostics(updated_reports)
        for report in updated_reports:
            report["trajectory_diagnostics"] = diagnostics
        return updated_reports

    def reconstruct_track(
        self,
        points: list[TrajectoryPoint],
        class_id: int,
    ) -> list[dict[str, Any]]:
        if len(points) < 3:
            return [
                self._empty_reconstruction(point, "insufficient_samples")
                for point in points
            ]

        profile = self.motion_router.route_class(class_id)
        timestamps = np.array([point.timestamp_sec for point in points], dtype=np.float64)
        xs = np.array([point.world_x for point in points], dtype=np.float64)
        ys = np.array([point.world_y for point in points], dtype=np.float64)
        xs, ys = self._repair_outliers(
            timestamps,
            xs,
            ys,
            profile.hard_max_speed_kmh or profile.max_speed_kmh,
        )
        xs = self._smooth_series(timestamps, xs, class_id)
        ys = self._smooth_series(timestamps, ys, class_id)
        xs, ys = self._kalman_rts_smooth(timestamps, xs, ys, profile.process_noise)
        velocities = self._velocities(timestamps, xs, ys)
        speeds = np.linalg.norm(velocities, axis=1) * 3.6
        accelerations = self._accelerations(timestamps, speeds)
        metrics = compute_speed_stability(
            timestamps.tolist(),
            [float(speed) for speed in speeds],
            [None if value is None else float(value) for value in accelerations],
        )
        return [
            self._point_result(
                point,
                xs[index],
                ys[index],
                velocities[index],
                speeds[index],
                accelerations[index],
                metrics,
            )
            for index, point in enumerate(points)
        ]

    @staticmethod
    def _group_points(frame_reports: list[dict[str, Any]]) -> dict[int, list[TrajectoryPoint]]:
        grouped: dict[int, list[TrajectoryPoint]] = {}
        for report_index, report in enumerate(frame_reports):
            timestamp = float(report.get("timestamp_sec", 0.0))
            for track in report.get("active_tracks", []):
                if not isinstance(track, dict):
                    continue
                tracker_id = int(track.get("tracker_id", -1))
                world_x = track.get("ground_x_m")
                world_y = track.get("ground_y_m")
                if world_x is None or world_y is None:
                    continue
                grouped.setdefault(tracker_id, []).append(
                    TrajectoryPoint(
                        report_index=report_index,
                        timestamp_sec=timestamp,
                        world_x=float(world_x),
                        world_y=float(world_y),
                        raw_speed_kmh=(
                            float(track["speed_kmh"])
                            if track.get("speed_kmh") is not None
                            else None
                        ),
                        reconstructed=bool(track.get("reconstructed", False)),
                    )
                )
        return grouped

    @staticmethod
    def _fill_short_gaps(
        frame_reports: list[dict[str, Any]],
        points: list[TrajectoryPoint],
        max_gap_frames: int = 3,
    ) -> list[TrajectoryPoint]:
        if len(points) < 2:
            return points
        by_index = {point.report_index: point for point in points}
        filled: list[TrajectoryPoint] = []
        sorted_points = sorted(points, key=lambda point: point.report_index)
        for left, right in zip(sorted_points, sorted_points[1:], strict=False):
            filled.append(left)
            frame_gap = right.report_index - left.report_index
            if frame_gap <= 1 or frame_gap > max_gap_frames:
                continue
            for report_index in range(left.report_index + 1, right.report_index):
                if report_index in by_index or report_index >= len(frame_reports):
                    continue
                ratio = (report_index - left.report_index) / frame_gap
                report = frame_reports[report_index]
                timestamp = float(report.get("timestamp_sec", left.timestamp_sec))
                filled.append(
                    TrajectoryPoint(
                        report_index=report_index,
                        timestamp_sec=timestamp,
                        world_x=left.world_x + (right.world_x - left.world_x) * ratio,
                        world_y=left.world_y + (right.world_y - left.world_y) * ratio,
                        raw_speed_kmh=None,
                        reconstructed=True,
                    )
                )
        filled.append(sorted_points[-1])
        return sorted(filled, key=lambda point: point.report_index)

    @staticmethod
    def _trajectory_diagnostics(frame_reports: list[dict[str, Any]]) -> dict[str, object]:
        total_track_entries = 0
        reconstructed_entries = 0
        low_confidence_entries = 0
        id_switch_risk_entries = 0
        speed_frozen_entries = 0
        bev_rejected_entries = 0
        contact_low_confidence_entries = 0
        track_frame_indices: dict[int, list[int]] = {}
        for report_index, report in enumerate(frame_reports):
            for track in report.get("active_tracks", []):
                if not isinstance(track, dict):
                    continue
                total_track_entries += 1
                if bool(track.get("reconstructed", False)):
                    reconstructed_entries += 1
                if track.get("quality_label") == "low_confidence" or not bool(
                    track.get("physics_valid", True),
                ):
                    low_confidence_entries += 1
                if float(track.get("id_switch_risk") or 0.0) >= 0.75:
                    id_switch_risk_entries += 1
                if bool(track.get("speed_frozen", False)):
                    speed_frozen_entries += 1
                if track.get("bev_risk_level") == "rejected":
                    bev_rejected_entries += 1
                if float(track.get("contact_fusion_confidence") or 1.0) < 0.45:
                    contact_low_confidence_entries += 1
                tracker_id = int(track.get("tracker_id", -1))
                if tracker_id >= 0:
                    track_frame_indices.setdefault(tracker_id, []).append(report_index)
        fragmentation_count = 0
        for indices in track_frame_indices.values():
            ordered = sorted(set(indices))
            fragmentation_count += sum(
                1
                for previous, current in zip(ordered, ordered[1:], strict=False)
                if current - previous > 1
            )
        reconstructed_gap_runs = 0
        for tracker_id, indices in track_frame_indices.items():
            reconstructed_indices = {
                report_index
                for report_index in indices
                for track in frame_reports[report_index].get("active_tracks", [])
                if isinstance(track, dict)
                and int(track.get("tracker_id", -1)) == tracker_id
                and bool(track.get("reconstructed", False))
            }
            ordered_reconstructed = sorted(reconstructed_indices)
            if ordered_reconstructed:
                reconstructed_gap_runs += 1
                reconstructed_gap_runs += sum(
                    1
                    for previous, current in zip(
                        ordered_reconstructed,
                        ordered_reconstructed[1:],
                        strict=False,
                    )
                    if current - previous > 1
                )
        fragmentation_count = max(fragmentation_count, reconstructed_gap_runs)
        denominator = max(total_track_entries, 1)
        return {
            "track_entry_count": total_track_entries,
            "reconstructed_track_entries": reconstructed_entries,
            "reconstructed_ratio": reconstructed_entries / denominator,
            "low_confidence_ratio": low_confidence_entries / denominator,
            "track_fragmentation_count": fragmentation_count,
            "id_switch_risk_count": id_switch_risk_entries,
            "speed_frozen_ratio": speed_frozen_entries / denominator,
            "bev_rejected_ratio": bev_rejected_entries / denominator,
            "contact_fusion_low_confidence_ratio": (
                contact_low_confidence_entries / denominator
            ),
            "model_reference": "trajectory_gap_fill + kalman_rts_smoother",
        }

    @staticmethod
    def _class_id_for_track(frame_reports: list[dict[str, Any]], tracker_id: int) -> int | None:
        for report in frame_reports:
            for track in report.get("active_tracks", []):
                if isinstance(track, dict) and int(track.get("tracker_id", -1)) == tracker_id:
                    return int(track.get("class_id", -1))
        return None

    @staticmethod
    def _copy_report(report: dict[str, Any]) -> dict[str, Any]:
        copied = dict(report)
        copied["active_tracks"] = [
            dict(track) if isinstance(track, dict) else track
            for track in report.get("active_tracks", [])
        ]
        return copied

    @staticmethod
    def _repair_outliers(
        timestamps: np.ndarray,
        xs: np.ndarray,
        ys: np.ndarray,
        hard_max_speed_kmh: float,
    ) -> tuple[np.ndarray, np.ndarray]:
        if len(timestamps) < 4:
            return xs, ys
        repaired_x = xs.copy()
        repaired_y = ys.copy()
        delta_t = np.diff(timestamps)
        valid_delta = delta_t > 1e-6
        if not np.any(valid_delta):
            return repaired_x, repaired_y
        step_distances = np.linalg.norm(np.diff(np.column_stack([xs, ys]), axis=0), axis=1)
        step_speeds = np.zeros_like(step_distances)
        step_speeds[valid_delta] = step_distances[valid_delta] / delta_t[valid_delta] * 3.6
        outlier = np.zeros(len(timestamps), dtype=bool)
        outlier[1:] |= step_speeds > hard_max_speed_kmh
        outlier[:-1] |= step_speeds > hard_max_speed_kmh
        fit = np.polyfit(timestamps, xs, deg=1), np.polyfit(timestamps, ys, deg=1)
        expected_x = np.polyval(fit[0], timestamps)
        expected_y = np.polyval(fit[1], timestamps)
        residual = np.linalg.norm(
            np.column_stack([xs - expected_x, ys - expected_y]),
            axis=1,
        )
        median_residual = float(np.median(residual))
        mad = float(np.median(np.abs(residual - median_residual)))
        residual_gate = max(2.0, median_residual + 4.0 * max(mad, 1e-6))
        outlier |= residual > residual_gate
        if not np.any(outlier) or np.count_nonzero(~outlier) < 3:
            return repaired_x, repaired_y
        valid = ~outlier
        repaired_x[outlier] = np.interp(timestamps[outlier], timestamps[valid], xs[valid])
        repaired_y[outlier] = np.interp(timestamps[outlier], timestamps[valid], ys[valid])
        return repaired_x, repaired_y

    @staticmethod
    def _smooth_series(timestamps: np.ndarray, values: np.ndarray, class_id: int) -> np.ndarray:
        if len(values) < 5:
            return values
        try:
            from scipy.signal import savgol_filter
        except ImportError:
            return values
        median_dt = float(np.median(np.diff(timestamps))) if len(timestamps) > 1 else 1.0 / 30.0
        window_sec = 2.5 if class_id in MotionRouter.VEHICLE_CLASS_IDS else 1.8
        window = max(5, int(round(window_sec / max(median_dt, 1e-3))))
        window = min(window, len(values))
        if window % 2 == 0:
            window -= 1
        if window < 5:
            return values
        return savgol_filter(values, window_length=window, polyorder=2, mode="interp")

    @staticmethod
    def _kalman_rts_smooth(
        timestamps: np.ndarray,
        xs: np.ndarray,
        ys: np.ndarray,
        process_noise: str,
    ) -> tuple[np.ndarray, np.ndarray]:
        if len(xs) < 3:
            return xs, ys
        q = 0.05 if process_noise == "low" else 0.45
        r = 0.18 if process_noise == "low" else 0.30
        count = len(xs)
        observations = np.column_stack([xs, ys]).astype(np.float64)
        states = np.zeros((count, 4, 1), dtype=np.float64)
        covariances = np.zeros((count, 4, 4), dtype=np.float64)
        predicted_states = np.zeros_like(states)
        predicted_covariances = np.zeros_like(covariances)
        initial_velocity = TrajectoryReconstructor._initial_velocity(timestamps, xs, ys)
        states[0] = np.array(
            [[xs[0]], [ys[0]], [initial_velocity[0]], [initial_velocity[1]]],
            dtype=np.float64,
        )
        covariances[0] = np.diag([r, r, 10.0, 10.0]).astype(np.float64)
        observation_matrix = np.array(
            [[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0]],
            dtype=np.float64,
        )
        measurement_covariance = np.eye(2, dtype=np.float64) * r
        identity = np.eye(4, dtype=np.float64)

        for index in range(1, count):
            delta_t = max(float(timestamps[index] - timestamps[index - 1]), 1e-3)
            transition = TrajectoryReconstructor._transition_matrix(delta_t)
            process_covariance = TrajectoryReconstructor._process_covariance(delta_t, q)
            predicted_states[index] = transition @ states[index - 1]
            predicted_covariances[index] = (
                transition @ covariances[index - 1] @ transition.T + process_covariance
            )
            measurement = observations[index].reshape(2, 1)
            innovation = measurement - observation_matrix @ predicted_states[index]
            innovation_covariance = (
                observation_matrix @ predicted_covariances[index] @ observation_matrix.T
                + measurement_covariance
            )
            gain = (
                predicted_covariances[index]
                @ observation_matrix.T
                @ np.linalg.pinv(innovation_covariance)
            )
            states[index] = predicted_states[index] + gain @ innovation
            covariances[index] = (identity - gain @ observation_matrix) @ predicted_covariances[
                index
            ]

        smoothed_states = states.copy()
        smoothed_covariances = covariances.copy()
        for index in range(count - 2, -1, -1):
            delta_t = max(float(timestamps[index + 1] - timestamps[index]), 1e-3)
            transition = TrajectoryReconstructor._transition_matrix(delta_t)
            predicted_covariance = predicted_covariances[index + 1]
            smoother_gain = (
                covariances[index] @ transition.T @ np.linalg.pinv(predicted_covariance)
            )
            smoothed_states[index] = states[index] + smoother_gain @ (
                smoothed_states[index + 1] - predicted_states[index + 1]
            )
            smoothed_covariances[index] = covariances[index] + smoother_gain @ (
                smoothed_covariances[index + 1] - predicted_covariance
            ) @ smoother_gain.T

        return smoothed_states[:, 0, 0], smoothed_states[:, 1, 0]

    @staticmethod
    def _ema(values: np.ndarray, alpha: float) -> np.ndarray:
        smoothed = values.copy()
        for index in range(1, len(values)):
            smoothed[index] = alpha * values[index] + (1.0 - alpha) * smoothed[index - 1]
        return smoothed

    @staticmethod
    def _velocities(timestamps: np.ndarray, xs: np.ndarray, ys: np.ndarray) -> np.ndarray:
        velocities = np.zeros((len(timestamps), 2), dtype=np.float64)
        if len(timestamps) < 2:
            return velocities
        velocities[:, 0] = np.gradient(xs, timestamps, edge_order=1)
        velocities[:, 1] = np.gradient(ys, timestamps, edge_order=1)
        return velocities

    @staticmethod
    def _accelerations(timestamps: np.ndarray, speeds_kmh: np.ndarray) -> list[float | None]:
        if len(timestamps) < 2:
            return [None for _ in speeds_kmh]
        speed_mps = speeds_kmh / 3.6
        acceleration = np.gradient(speed_mps, timestamps, edge_order=1)
        return [float(value) for value in acceleration]

    @staticmethod
    def _apply_track(
        reports: list[dict[str, Any]],
        tracker_id: int,
        class_id: int,
        reconstructed: list[dict[str, Any]],
    ) -> None:
        by_report = {int(item["report_index"]): item for item in reconstructed}
        for report_index, report in enumerate(reports):
            item = by_report.get(report_index)
            if item is None:
                continue
            active_tracks = report.setdefault("active_tracks", [])
            found = False
            for track in active_tracks:
                if isinstance(track, dict) and int(track.get("tracker_id", -1)) == tracker_id:
                    track.update(
                        {
                            key: value
                            for key, value in item.items()
                            if key != "report_index"
                        }
                    )
                    found = True
                    break
            if not found and bool(item.get("reconstructed", False)):
                active_tracks.append(
                    {
                        "tracker_id": tracker_id,
                        "class_id": class_id,
                        "class_name": "reconstructed",
                        "confidence": 0.0,
                        **{
                            key: value
                            for key, value in item.items()
                            if key != "report_index"
                        },
                    }
                )

    @staticmethod
    def _point_result(
        point: TrajectoryPoint,
        world_x: float,
        world_y: float,
        velocity: np.ndarray,
        speed_kmh: float,
        acceleration: float | None,
        metrics: SpeedStabilityMetrics,
    ) -> dict[str, Any]:
        heading = None
        if abs(float(velocity[0])) > 1e-9 or abs(float(velocity[1])) > 1e-9:
            heading = (
                math.degrees(math.atan2(float(velocity[1]), float(velocity[0]))) + 360.0
            ) % 360.0
        quality_label = (
            "stable"
            if metrics.stability_label != "unstable_observation"
            else "low_confidence"
        )
        return {
            "report_index": float(point.report_index),
            "raw_speed_kmh": point.raw_speed_kmh,
            "speed_kmh": float(speed_kmh),
            "ground_x_m": float(world_x),
            "ground_y_m": float(world_y),
            "velocity_x_mps": float(velocity[0]),
            "velocity_y_mps": float(velocity[1]),
            "heading_deg": float(heading) if heading is not None else None,
            "acceleration_mps2": acceleration,
            "physics_valid": True,
            "quality_label": quality_label,
            "speed_stability_score": metrics.speed_stability_score,
            "speed_cv": metrics.speed_cv,
            "max_speed_jump_kmh": metrics.max_speed_jump_kmh,
            "speed_jump_p95_kmh": metrics.speed_jump_p95_kmh,
            "acceleration_p95_mps2": metrics.acceleration_p95_mps2,
            "jerk_p95_mps3": metrics.jerk_p95_mps3,
            "stability_label": metrics.stability_label,
            "reconstructed": point.reconstructed,
        }

    @staticmethod
    def _empty_reconstruction(
        point: TrajectoryPoint,
        label: str,
    ) -> dict[str, Any]:
        return {
            "report_index": float(point.report_index),
            "raw_speed_kmh": point.raw_speed_kmh,
            "speed_stability_score": 0.0,
            "speed_cv": None,
            "max_speed_jump_kmh": None,
            "speed_jump_p95_kmh": None,
            "acceleration_p95_mps2": None,
            "jerk_p95_mps3": None,
            "stability_label": label,
            "reconstructed": point.reconstructed,
        }

    @staticmethod
    def _initial_velocity(
        timestamps: np.ndarray,
        xs: np.ndarray,
        ys: np.ndarray,
    ) -> tuple[float, float]:
        duration = max(float(timestamps[-1] - timestamps[0]), 1e-3)
        return (float((xs[-1] - xs[0]) / duration), float((ys[-1] - ys[0]) / duration))

    @staticmethod
    def _transition_matrix(delta_t: float) -> np.ndarray:
        return np.array(
            [
                [1.0, 0.0, delta_t, 0.0],
                [0.0, 1.0, 0.0, delta_t],
                [0.0, 0.0, 1.0, 0.0],
                [0.0, 0.0, 0.0, 1.0],
            ],
            dtype=np.float64,
        )

    @staticmethod
    def _process_covariance(delta_t: float, q: float) -> np.ndarray:
        dt2 = delta_t**2
        dt3 = delta_t**3
        dt4 = delta_t**4
        return np.array(
            [
                [dt4 / 4.0, 0.0, dt3 / 2.0, 0.0],
                [0.0, dt4 / 4.0, 0.0, dt3 / 2.0],
                [dt3 / 2.0, 0.0, dt2, 0.0],
                [0.0, dt3 / 2.0, 0.0, dt2],
            ],
            dtype=np.float64,
        ) * q
