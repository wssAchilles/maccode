from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Protocol, cast

import numpy as np
from domain.calibration.bev_confidence import BEVConfidenceMap, BEVConfidenceMapBuilder
from domain.calibration.candidate_evaluation import (
    CalibrationCandidateEvaluation,
    CalibrationCandidateEvaluator,
)
from domain.calibration.models import CalibrationPoint, HomographyResult
from domain.calibration.monte_carlo import CalibrationMonteCarloAnalyzer
from domain.calibration.sensitivity import (
    CalibrationSensitivityAnalyzer,
    CalibrationSensitivityReport,
)
from domain.calibration.service import CalibrationService
from domain.crowd_density.models import CrowdDensityInput
from domain.crowd_density.service import CrowdDensityService
from domain.detection.models import Detections
from domain.motion.router import MotionRouter
from domain.reports.generators import ReportGenerator
from domain.speed.contact_fusion import ContactPointFusion, ContactPointObservation
from domain.speed.estimator import SpeedEstimator
from domain.speed.ground_contact import GroundContactCorrector, GroundContactPoint
from domain.speed.models import SpeedRecord
from domain.speed.nis_diagnostics import NISDiagnosticsAnalyzer
from domain.speed.posterior import SpeedPosteriorAnalyzer
from domain.speed.trajectory_reconstruction import TrajectoryReconstructor
from domain.speed.view_transformer import ViewTransformer
from domain.tracking.integrity import TrackingIntegrityMonitor, TrackingIntegrityResult
from domain.tracking.models import Track
from domain.traffic_flow.models import TrafficFlowInput
from domain.traffic_flow.service import TrafficFlowService
from domain.zones.models import ZoneConfig
from domain.zones.service import ZoneService

from infrastructure.cv.optical_flow import OpticalFlowObservation, OpticalFlowVelocityEstimator
from infrastructure.cv.pose_ground_contact import PoseGroundContactEstimator
from infrastructure.cv.processed_video_renderer import ProcessedVideoRenderer
from infrastructure.cv.traffic_light_state import TrafficLightStateEstimator


@dataclass(frozen=True)
class VideoFrame:
    image: object
    frame_index: int
    timestamp_sec: float


class DetectorProtocol(Protocol):
    def detect(self, frame: object, frame_index: int, timestamp_sec: float) -> Detections:
        ...


class TrackingCountingAdapterProtocol(Protocol):
    def track_and_count(
        self,
        detections: Detections,
        line_start: tuple[float, float],
        line_end: tuple[float, float],
        zone_name: str = "main_gate",
    ) -> Any:
        ...


class OpenCVVideoFrameSource:
    def __init__(
        self,
        video_path: str,
        max_frames: int | None = None,
        frame_stride: int = 1,
    ) -> None:
        self.video_path = video_path
        self.max_frames = max_frames
        self.frame_stride = frame_stride

    def frames(self) -> Iterable[VideoFrame]:
        try:
            import cv2  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError("opencv-python is required to read local videos") from exc

        capture = cv2.VideoCapture(self.video_path)
        if not capture.isOpened():
            raise ValueError(f"could not open video: {self.video_path}")
        fps = capture.get(cv2.CAP_PROP_FPS) or 24.0
        raw_frame_index = 0
        emitted_count = 0
        try:
            while True:
                if self.max_frames is not None and emitted_count >= self.max_frames:
                    break
                ok, frame = capture.read()
                if not ok:
                    break
                raw_frame_index += 1
                if (raw_frame_index - 1) % self.frame_stride != 0:
                    continue
                emitted_count += 1
                yield VideoFrame(
                    frame,
                    frame_index=raw_frame_index,
                    timestamp_sec=raw_frame_index / fps,
                )
        finally:
            capture.release()


class SupervisionVideoProcessor:
    def __init__(
        self,
        detector: DetectorProtocol,
        adapter: TrackingCountingAdapterProtocol,
        calibration: HomographyResult,
        zone: ZoneConfig,
        fps: float = 24.0,
        frame_width: int = 100,
        frame_height: int = 100,
        segment_width_m: float = 10.0,
        segment_length_m: float = 500.0,
        grid_spacing_m: float = 5.0,
        position_rmse_floor_m: float = 0.05,
        rendered_video_path: Path | None = None,
        rendered_video_fps: float | None = None,
        calibration_context: dict[str, object] | None = None,
        trajectory_reconstruction_enabled: bool = True,
        pose_enabled: bool = False,
        pose_model_path: str = "yolo11n-pose.pt",
        pose_device: str = "mps",
    ) -> None:
        self.detector = detector
        self.adapter = adapter
        self.calibration_context = calibration_context or {}
        self.calibration_candidate_evaluation = CalibrationCandidateEvaluator().evaluate(
            calibration,
            self.calibration_context,
            frame_width=frame_width,
            frame_height=frame_height,
        )
        self.calibration, self.runtime_homography_source = self._select_runtime_calibration(
            calibration,
            self.calibration_context,
            self.calibration_candidate_evaluation,
        )
        self.zone = zone
        self.fps = fps
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.segment_width_m = segment_width_m
        self.segment_length_m = segment_length_m
        self.grid_spacing_m = grid_spacing_m
        self.calibration_source = str(
            self.calibration_context.get("calibration_source") or "unknown",
        )
        self.validation_max_error_px = self._optional_float(
            self.calibration_context.get("validation_max_error_px"),
        )
        self.road_plane_polygon_world = self._world_polygon(
            self.calibration_context.get("road_plane_polygon_world"),
        )
        self.road_plane_polygon_pixel = self._world_polygon(
            self.calibration_context.get("road_plane_polygon_pixel"),
        )
        self.calibration_trusted = self._is_calibration_trusted()
        self.metric_speed_admitted, self.metric_speed_gate_reason = (
            self._metric_speed_gate()
        )
        self.scale_confidence_label, self.weak_calibration_reason = (
            self._scale_confidence()
        )
        self.motion_router = MotionRouter()
        self.view_transformer = ViewTransformer(self.calibration.homography_matrix)
        self.speed_estimator = SpeedEstimator(
            self.view_transformer,
            position_rmse_m=max(self.calibration.pixel_to_world_rmse_m, position_rmse_floor_m),
            timestamp_uncertainty_sec=1.0 / fps,
        )
        self.metric_plane_set = CalibrationService().build_metric_plane_set(
            metric_planes=self._metric_plane_configs(),
            default_control_points=self._calibration_points_from_context(),
            default_pixel_polygon=(
                self.road_plane_polygon_pixel or self._default_metric_pixel_polygon()
            ),
            default_world_polygon=(
                self.road_plane_polygon_world or self._default_metric_world_polygon()
            ),
            default_trusted=self.metric_speed_admitted,
            default_validation_segments=self._validation_segments_from_context(),
            default_homography=self.calibration,
        )
        self.plane_transformers = {
            plane.plane_id: ViewTransformer(plane.homography.homography_matrix)
            for plane in self.metric_plane_set.planes
        }
        self.trajectory_reconstruction_enabled = trajectory_reconstruction_enabled
        self.trajectory_reconstructor = TrajectoryReconstructor(self.motion_router)
        self.ground_contact_corrector = GroundContactCorrector()
        self.contact_point_fusion = ContactPointFusion()
        self.tracking_integrity_monitor = TrackingIntegrityMonitor()
        self.pose_ground_contact = (
            PoseGroundContactEstimator(pose_model_path, pose_device)
            if pose_enabled
            else None
        )
        self.optical_flow_estimator = OpticalFlowVelocityEstimator(
            self.speed_estimator.view_transformer,
        )
        self.report_generator = ReportGenerator()
        self.crowd_density = CrowdDensityService()
        self.signal_state_estimator = TrafficLightStateEstimator()
        self.traffic_flow = TrafficFlowService(
            free_flow_speed_kmh=40.0,
            jam_density_veh_per_km=100.0,
        )
        self.zone_service = ZoneService([zone])
        self.homography_grid = self._build_homography_grid()
        self.bev_confidence_map: BEVConfidenceMap = BEVConfidenceMapBuilder(
            self.view_transformer,
            frame_width=self.frame_width,
            frame_height=self.frame_height,
            road_plane_polygon_world=self.road_plane_polygon_world,
            validation_max_error_px=self.validation_max_error_px,
        ).build()
        self.plane_bev_confidence_maps: dict[str, BEVConfidenceMap] = {
            plane.plane_id: BEVConfidenceMapBuilder(
                self.plane_transformers[plane.plane_id],
                frame_width=self.frame_width,
                frame_height=self.frame_height,
                road_plane_polygon_world=plane.world_polygon,
                validation_max_error_px=self.validation_max_error_px,
            ).build()
            for plane in self.metric_plane_set.planes
            if plane.plane_id in self.plane_transformers
        }
        self.calibration_sensitivity: CalibrationSensitivityReport = (
            CalibrationSensitivityAnalyzer().analyze(
                self.calibration,
                self.bev_confidence_map,
                self.calibration_context,
            )
        )
        self.calibration_monte_carlo = CalibrationMonteCarloAnalyzer()
        self.speed_posterior_analyzer = SpeedPosteriorAnalyzer()
        self.nis_diagnostics_analyzer = NISDiagnosticsAnalyzer()
        self.frame_reports: list[dict[str, Any]] = []
        self._pixel_histories: dict[int, list[tuple[float, float]]] = {}
        self._latest_contact_points: dict[int, GroundContactPoint] = {}
        self._previous_frame_image: object | None = None
        self._previous_timestamp_sec: float | None = None
        self._previous_track_boxes: dict[int, list[float]] = {}
        self._previous_contact_points: dict[int, tuple[float, float]] = {}
        self._previous_track_metadata: dict[int, Track] = {}
        self._last_reliable_signal_state = "unknown"
        self._integrity_results: dict[int, TrackingIntegrityResult] = {}
        self._tracking_diagnostics: dict[str, object] = {}
        self._bev_checked_count = 0
        self._bev_rejected_count = 0
        self._speed_frozen_count = 0
        self._integrity_event_count = 0
        self._contact_fusion_count = 0
        self._contact_fusion_low_confidence_count = 0
        self._contact_outlier_count = 0
        self._optical_flow_checked_count = 0
        self._optical_flow_low_inlier_count = 0
        self._perspective_speed_inflation_count = 0
        self._pedestrian_physical_speed_gate_count = 0
        self._far_field_bbox_contact_weak_count = 0
        self._pedestrian_scale_drift_count = 0
        self._pedestrian_speed_suppressed_count = 0
        self._pose_geometry_used_count = 0
        self._bbox_height_consistency_fail_count = 0
        self.rendered_video_path = rendered_video_path
        self._renderer = (
            ProcessedVideoRenderer(
                rendered_video_path,
                frame_width=frame_width,
                frame_height=frame_height,
                fps=rendered_video_fps or min(max(fps, 1.0), 12.0),
                homography_grid=self.homography_grid,
            )
            if rendered_video_path is not None
            else None
        )

    def process_frames(self, frames: Iterable[VideoFrame]) -> dict[str, Any]:
        latest_report: dict[str, Any] | None = None
        self.frame_reports = []
        render_frames: list[object] = []
        try:
            for frame in frames:
                detections = self.detector.detect(
                    frame.image,
                    frame.frame_index,
                    frame.timestamp_sec,
                )
                adapter_result = self.adapter.track_and_count(
                    detections,
                    line_start=(float(self.zone.line_start[0]), float(self.zone.line_start[1])),
                    line_end=(float(self.zone.line_end[0]), float(self.zone.line_end[1])),
                    zone_name=self.zone.name,
                )
                self._tracking_diagnostics = self._adapter_tracking_diagnostics()
                tracks = list(adapter_result.tracks)
                zone_stats = self.zone_service.trigger(tracks)
                tracks.extend(
                    self._flow_gap_predictions(
                        tracks,
                        frame.image,
                        frame.frame_index,
                    )
                )
                self._update_pixel_histories(tracks)
                contact_points = self._update_track_speeds(
                    tracks,
                    frame.timestamp_sec,
                    frame.image,
                )
                speed_records = self.speed_estimator.get_all_records()
                flow = self._build_traffic_flow(tracks, speed_records, frame.timestamp_sec)
                regional_people_count = self._build_regional_people_count(tracks)
                infrastructure_semantics = self._build_infrastructure_semantics(
                    tracks,
                    frame.image,
                )
                safety_metrics = self._build_safety_metrics(
                    tracks,
                    speed_records,
                    infrastructure_semantics,
                )
                report = self.report_generator.add_frame(
                    frame_index=frame.frame_index,
                    timestamp_sec=frame.timestamp_sec,
                    tracks=tracks,
                    zone_stats=zone_stats,
                    fps=self.fps,
                    speed_records=speed_records,
                    calibration_quality=self.calibration.calibration_quality,
                    calibration_diagnostics=self._build_calibration_diagnostics(),
                    homography_grid=self.homography_grid,
                    traffic_flow=flow,
                    regional_people_count=regional_people_count,
                    infrastructure_semantics=infrastructure_semantics,
                    safety_metrics=safety_metrics,
                    bev_confidence_map=self.bev_confidence_map.to_dict(),
                    integrity_diagnostics=self._build_integrity_diagnostics(),
                    calibration_sensitivity=self.calibration_sensitivity.to_dict(),
                    speed_nis_diagnostics=self._speed_nis_diagnostics(speed_records),
                    speed_geometry_diagnostics=self._build_speed_geometry_diagnostics(),
                )
                latest_report = report.to_dict()
                self.frame_reports.append(latest_report)
                if self._renderer is not None:
                    render_frames.append(frame.image)
                self._remember_optical_flow_state(
                    tracks,
                    contact_points,
                    frame.image,
                    frame.timestamp_sec,
                )
            if latest_report is not None and self.trajectory_reconstruction_enabled:
                self.frame_reports = self.trajectory_reconstructor.reconstruct_reports(
                    self.frame_reports,
                )
                latest_report = self.frame_reports[-1]
            if self._renderer is not None:
                for frame_image, frame_report in zip(
                    render_frames,
                    self.frame_reports,
                    strict=False,
                ):
                    self._renderer.render(frame_image, frame_report)
        finally:
            if self._renderer is not None:
                self._renderer.close()

        if latest_report is None:
            raise ValueError("no frames were processed")
        return latest_report

    def _build_calibration_diagnostics(self) -> dict[str, object]:
        error_sources = [
            "homography calibration residual",
            "detector bounding-box jitter",
            "frame timestamp quantization",
            "perspective extrapolation outside calibrated road plane",
        ]
        if not self.calibration_trusted:
            error_sources.append("untrusted_calibration_grid_suppressed")
        diagnostics = {
            "homography_model": "RANSAC planar homography, pixel(u,v) -> ground(X,Y)",
            "calibration_source": self.calibration_source,
            "calibration_trusted": self.calibration_trusted,
            "metric_speed_admitted": self.metric_speed_admitted,
            "metric_speed_gate_reason": self.metric_speed_gate_reason,
            "metric_planes": self.metric_plane_set.to_diagnostics(),
            "plane_validation_errors": {
                plane.plane_id: plane.homography.world_to_pixel_rmse_px
                for plane in self.metric_plane_set.planes
            },
            "camera_profile_id": self.calibration_context.get("camera_profile_id"),
            "camera_profile_display_name": self.calibration_context.get(
                "camera_profile_display_name",
            ),
            "camera_profile_role": self.calibration_context.get("camera_profile_role"),
            "profile_reuse_note": self.calibration_context.get("profile_reuse_note"),
            "profile_polygon_zones": self.calibration_context.get("profile_polygon_zones", []),
            "profile_traffic_light_rois": self.calibration_context.get(
                "profile_traffic_light_rois",
                [],
            ),
            "profile_risk_areas": self.calibration_context.get("profile_risk_areas", []),
            "auto_calibration": self.calibration_context.get("auto_calibration"),
            "frame_geometry_evidence": self.calibration_context.get(
                "frame_geometry_evidence",
            ),
            "calibration_quality": self.calibration.calibration_quality,
            "pixel_to_world_rmse_m": self.calibration.pixel_to_world_rmse_m,
            "world_to_pixel_rmse_px": self.calibration.world_to_pixel_rmse_px,
            "reprojection_rmse_px": self.calibration.world_to_pixel_rmse_px,
            "validation_max_error_px": self.validation_max_error_px,
            "camera_intrinsics_prior": self.calibration_context.get(
                "camera_intrinsics_prior",
                {},
            ),
            "camera_mount_prior": self.calibration_context.get("camera_mount_prior", {}),
            "vehicle_3d_priors": self.calibration_context.get("vehicle_3d_priors", {}),
            "vehicle_3d_observations": self.calibration_context.get(
                "vehicle_3d_observations",
                [],
            ),
            "calibration_3d_diagnostics": self.calibration_context.get(
                "calibration_3d_diagnostics",
                {},
            ),
            "inlier_count": self.calibration.inlier_count,
            "condition_number": self.calibration.condition_number,
            "position_rmse_m": self.speed_estimator.position_rmse_m,
            "timestamp_uncertainty_sec": self.speed_estimator.timestamp_uncertainty_sec,
            "local_error_model": (
                "homography_jacobian_pixel_covariance -> world_position_sigma"
            ),
            "calibration_risk_gate": (
                "trusted_source && quality != unstable && validation_max_error_px <= 15"
            ),
            "error_sources": error_sources,
            "model_reference": "Model 1 + Model 3 + Model 6 + Model 10",
            "runtime_homography_source": self.runtime_homography_source,
            "auto_geometry_evidence": self._auto_geometry_evidence(),
            "vanishing_point_count": self._vanishing_point_count(),
            "lane_width_prior_m": self._lane_width_prior_m(),
            "vehicle_size_prior_used": self._vehicle_size_prior_used(),
            "weak_scale_mode": self.scale_confidence_label == "weak_scale",
            "weak_calibration_reason": self.weak_calibration_reason,
            "pedestrian_geometry_self_supervision": {
                "pedestrian_scale_drift_count": self._pedestrian_scale_drift_count,
                "pedestrian_speed_suppressed_count": (
                    self._pedestrian_speed_suppressed_count
                ),
                "pose_geometry_used_count": self._pose_geometry_used_count,
                "bbox_height_consistency_fail_count": (
                    self._bbox_height_consistency_fail_count
                ),
                "model_reference": "pedestrian_head_foot_scale_drift_v1",
            },
        }
        diagnostics.update(self.calibration_candidate_evaluation.to_diagnostics())
        diagnostics["calibration_sensitivity"] = self.calibration_sensitivity.to_dict()
        selected_score = next(
            (
                score.score
                for score in self.calibration_candidate_evaluation.scores
                if score.candidate_id
                == self.calibration_candidate_evaluation.selected_candidate_id
            ),
            None,
        )
        diagnostics["calibration_candidate_score"] = selected_score
        return diagnostics

    def _calibration_uncertainty_band(
        self,
        speed_kmh: float | None,
    ) -> list[float | None] | None:
        if speed_kmh is None:
            return None
        sensitivity = self.calibration_sensitivity.speed_sensitivity_p95
        if self.scale_confidence_label == "weak_scale":
            sensitivity = max(sensitivity, 0.18)
        margin = max(0.0, speed_kmh * sensitivity)
        return [float(max(0.0, speed_kmh - margin)), float(speed_kmh + margin)]

    def _calibration_speed_posterior(
        self,
        record: SpeedRecord | None,
    ) -> dict[str, object] | None:
        if record is None or record.speed_kmh is None or not record.physics_valid:
            return None
        return self.calibration_monte_carlo.analyze(
            self.calibration,
            speed_kmh=record.speed_kmh,
            sample_count=200,
            random_seed=17,
        ).to_dict()

    def _joint_speed_posterior(
        self,
        record: SpeedRecord | None,
    ) -> dict[str, object] | None:
        if record is None or record.speed_kmh is None or not record.physics_valid:
            return None
        return self.speed_posterior_analyzer.analyze(
            record,
            self.calibration,
            timestamp_uncertainty_sec=self.speed_estimator.timestamp_uncertainty_sec,
            sample_count=200,
            random_seed=23,
        ).to_dict()

    def _speed_nis_diagnostics(
        self,
        speed_records: dict[int, SpeedRecord],
    ) -> dict[str, object]:
        return self.nis_diagnostics_analyzer.analyze(speed_records).to_dict()

    @staticmethod
    def _select_runtime_calibration(
        calibration: HomographyResult,
        calibration_context: dict[str, object],
        evaluation: CalibrationCandidateEvaluation,
    ) -> tuple[HomographyResult, str]:
        if evaluation.selected_candidate_id != "manual_runtime_preset":
            candidate = next(
                (
                    item
                    for item in evaluation.candidates
                    if item.candidate_id == evaluation.selected_candidate_id
                ),
                None,
            )
            if candidate is not None:
                return (
                    HomographyResult(
                        homography_matrix=candidate.homography_matrix,
                        reprojection_rmse=calibration.reprojection_rmse,
                        pixel_to_world_rmse_m=max(
                            calibration.pixel_to_world_rmse_m,
                            candidate.metrics.get("control_point_residual_m") or 0.0,
                        ),
                        world_to_pixel_rmse_px=calibration.world_to_pixel_rmse_px,
                        inlier_count=calibration.inlier_count,
                        condition_number=calibration.condition_number,
                        inlier_mask=list(calibration.inlier_mask),
                        calibration_quality=calibration.calibration_quality,
                        refinement_applied=calibration.refinement_applied,
                        refinement_initial_rmse_m=calibration.refinement_initial_rmse_m,
                        refinement_final_rmse_m=calibration.refinement_final_rmse_m,
                        refinement_iterations=calibration.refinement_iterations,
                        runtime_homography_source=candidate.source,
                    ),
                    candidate.source,
                )
        return calibration, calibration.runtime_homography_source

    def _build_homography_grid(self) -> dict[str, object] | None:
        if not self.calibration_trusted:
            return None
        return CalibrationService().build_homography_grid(
            self.calibration,
            frame_width=self.frame_width,
            frame_height=self.frame_height,
            world_width_m=self.segment_width_m,
            world_length_m=self.segment_length_m,
            spacing_m=self.grid_spacing_m,
            calibration_source=self.calibration_source,
            calibration_trusted=True,
            road_plane_polygon_world=self.road_plane_polygon_world,
            validation_max_error_px=self.validation_max_error_px,
        ).to_dict()

    def _is_calibration_trusted(self) -> bool:
        trusted_sources = {"video_manual_preset", "camera_manual_preset", "synthetic_demo"}
        if self.calibration_source not in trusted_sources:
            return False
        if self.calibration.calibration_quality == "unstable":
            return False
        if not bool(self.calibration_context.get("calibration_trusted", False)):
            return False
        if (
            self.validation_max_error_px is not None
            and self.validation_max_error_px > 15.0
        ):
            return False
        return True

    def _metric_speed_gate(self) -> tuple[bool, str | None]:
        has_trusted_metric_plane = any(
            bool(plane.get("trusted", plane.get("calibration_trusted", False)))
            for plane in self._metric_plane_configs()
        )
        if has_trusted_metric_plane:
            return True, None
        if not self.calibration_trusted:
            return False, "metric_calibration_not_trusted"
        if self.calibration_source == "synthetic_demo":
            return True, None
        control_point_count = self._optional_int(
            self.calibration_context.get("manual_control_point_count"),
        )
        if control_point_count is not None and control_point_count < 4:
            return False, "insufficient_metric_ground_control_points"
        independent_segment_count = self._optional_int(
            self.calibration_context.get("independent_validation_segment_count"),
        )
        if independent_segment_count is not None and independent_segment_count < 1:
            return False, "missing_independent_metric_validation_segment"
        if self.calibration.world_to_pixel_rmse_px > 15.0:
            return False, "world_to_pixel_rmse_gate_failed"
        if self.calibration.pixel_to_world_rmse_m > 2.0:
            return False, "pixel_to_world_rmse_gate_failed"
        if self.calibration.condition_number > 1e8:
            return False, "homography_condition_number_gate_failed"
        return True, None

    def _scale_confidence(self) -> tuple[str, str | None]:
        if self.metric_speed_admitted and self.calibration_source in {
            "video_manual_preset",
            "camera_manual_preset",
            "synthetic_demo",
        }:
            return "stable", None
        if self.calibration_trusted and not self.metric_speed_admitted:
            return "weak_scale", self.metric_speed_gate_reason
        if self.runtime_homography_source == "auto_vp_lane_vehicle_size_candidate":
            return "weak_scale", "auto_geometry_prior_runtime_candidate"
        if self.calibration_context.get("auto_calibration"):
            return "weak_scale", "auto_geometry_evidence_not_fully_trusted"
        return "weak_scale", "calibration_source_not_trusted"

    def _auto_geometry_evidence(self) -> dict[str, object]:
        auto = self.calibration_context.get("auto_calibration")
        if not isinstance(auto, dict):
            return {
                "available": False,
                "lane_width_prior_m": self._lane_width_prior_m(),
                "vehicle_size_prior_used": self._vehicle_size_prior_used(),
            }
        return {
            "available": True,
            "confidence": auto.get("auto_calibration_confidence"),
            "quality_issues": auto.get("quality_issues", []),
            "vanishing_point_count": self._vanishing_point_count(),
            "lane_width_prior_m": self._lane_width_prior_m(),
            "vehicle_size_prior_used": self._vehicle_size_prior_used(),
        }

    def _vanishing_point_count(self) -> int:
        auto = self.calibration_context.get("auto_calibration")
        if not isinstance(auto, dict):
            return 0
        points = auto.get("vanishing_points")
        return len(points) if isinstance(points, list) else 0

    def _lane_width_prior_m(self) -> float:
        for key in ("lane_width_prior_m", "lane_width_m"):
            value = self.calibration_context.get(key)
            if isinstance(value, (int, float)) and value > 0:
                return float(value)
        return 3.5

    def _vehicle_size_prior_used(self) -> bool:
        vehicle_priors = self.calibration_context.get("vehicle_3d_priors")
        if isinstance(vehicle_priors, dict) and vehicle_priors:
            return True
        auto = self.calibration_context.get("auto_calibration")
        return isinstance(auto, dict) and bool(auto.get("vehicle_size_prior_used"))

    @staticmethod
    def _optional_float(value: object) -> float | None:
        if value is None or isinstance(value, bool):
            return None
        if not isinstance(value, (int, float, str)):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _optional_int(value: object) -> int | None:
        if value is None or isinstance(value, bool):
            return None
        if not isinstance(value, (int, float, str)):
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _metric_plane_configs(self) -> list[dict[str, object]]:
        value = self.calibration_context.get("metric_planes")
        if not isinstance(value, list):
            return []
        return [dict(item) for item in value if isinstance(item, dict)]

    def _calibration_points_from_context(self) -> list[CalibrationPoint]:
        raw_points = self.calibration_context.get("manual_control_points")
        if not isinstance(raw_points, list):
            return []
        points: list[CalibrationPoint] = []
        for item in raw_points:
            if not isinstance(item, dict):
                return []
            try:
                points.append(
                    CalibrationPoint(
                        pixel_x=float(item["pixel_x"]),
                        pixel_y=float(item["pixel_y"]),
                        world_x=float(item["world_x"]),
                        world_y=float(item["world_y"]),
                    )
                )
            except (KeyError, TypeError, ValueError):
                return []
        return points

    def _validation_segments_from_context(self) -> list[dict[str, object]]:
        value = self.calibration_context.get("validation_segments")
        if not isinstance(value, list):
            return []
        return [dict(item) for item in value if isinstance(item, dict)]

    def _default_metric_pixel_polygon(self) -> list[tuple[float, float]]:
        return [
            (0.0, 0.0),
            (float(self.frame_width), 0.0),
            (float(self.frame_width), float(self.frame_height)),
            (0.0, float(self.frame_height)),
        ]

    def _default_metric_world_polygon(self) -> list[tuple[float, float]]:
        return [
            self.view_transformer.transform_point(x, y)
            for x, y in self._default_metric_pixel_polygon()
        ]

    @staticmethod
    def _world_polygon(value: object) -> list[tuple[float, float]] | None:
        if not isinstance(value, list):
            return None
        polygon: list[tuple[float, float]] = []
        for point in value:
            if not isinstance(point, (list, tuple)) or len(point) != 2:
                return None
            try:
                polygon.append((float(point[0]), float(point[1])))
            except (TypeError, ValueError):
                return None
        return polygon if len(polygon) >= 3 else None

    def _update_track_speeds(
        self,
        tracks: list[Track],
        timestamp_sec: float,
        frame_image: object,
    ) -> dict[int, GroundContactPoint]:
        contact_points: dict[int, GroundContactPoint] = {}
        active_ids = {track.tracker_id for track in tracks}
        for track in tracks:
            bbox_contact_point = self.ground_contact_corrector.correct(
                tracker_id=track.tracker_id,
                class_id=track.class_id,
                xyxy=track.xyxy,
                timestamp_sec=timestamp_sec,
            )
            pose_contact_point = (
                self.pose_ground_contact.estimate(frame_image, track)
                if self.pose_ground_contact is not None
                else None
            )
            if pose_contact_point is not None:
                self._pose_geometry_used_count += 1
            flow_contact_point = self._flow_refined_contact_point(track, frame_image)
            contact_point = self._fuse_contact_point(
                bbox_contact_point,
                pose_contact_point,
                flow_contact_point,
            )
            contact_points[track.tracker_id] = contact_point
            self._latest_contact_points[track.tracker_id] = contact_point
            profile = self.motion_router.route_class(track.class_id)
            if not profile.should_estimate_speed:
                continue

            self._contact_fusion_count += 1
            if (contact_point.fusion_confidence or contact_point.confidence) < 0.45:
                self._contact_fusion_low_confidence_count += 1
            if contact_point.outlier_sources:
                self._contact_outlier_count += 1
            if not self.metric_speed_admitted:
                self.speed_estimator.view_transformer = self.view_transformer
                self.speed_estimator.suppress_measurement(
                    tracker_id=track.tracker_id,
                    pixel_point=contact_point.pixel,
                    timestamp_sec=timestamp_sec,
                    quality_label="weak_scale",
                    rejection_reason=(
                        self.metric_speed_gate_reason
                        or "metric_calibration_not_trusted"
                    ),
                    preserve_previous_speed=False,
                    measurement_source=contact_point.measurement_source,
                    measurement_confidence=contact_point.confidence,
                    scale_confidence_label=self.scale_confidence_label,
                    weak_calibration_reason=self.weak_calibration_reason,
                    speed_geometry_diagnostics=self._speed_geometry_diagnostics(
                        track,
                        contact_point,
                        plane_id=None,
                        plane_status="not_admitted",
                        plane_reason=self.metric_speed_gate_reason,
                    ),
                )
                self.speed_estimator.annotate_record(
                    track.tracker_id,
                    contact_fusion_sources=contact_point.fusion_sources,
                    contact_fusion_weights=contact_point.fusion_weights,
                    contact_pixel_covariance=contact_point.pixel_covariance,
                    contact_fusion_confidence=contact_point.fusion_confidence,
                    contact_outlier_source=self._joined_sources(contact_point.outlier_sources),
                    contact_innovation_score=contact_point.innovation_score,
                )
                continue
            plane_selection = self.metric_plane_set.select(contact_point.pixel)
            selected_plane = plane_selection.plane
            if selected_plane is None:
                self.speed_estimator.suppress_measurement(
                    tracker_id=track.tracker_id,
                    pixel_point=contact_point.pixel,
                    timestamp_sec=timestamp_sec,
                    quality_label="geometry_invalid",
                    rejection_reason=plane_selection.reason or "plane_unresolved",
                    preserve_previous_speed=True,
                    measurement_source=contact_point.measurement_source,
                    measurement_confidence=contact_point.confidence,
                    scale_confidence_label=self.scale_confidence_label,
                    weak_calibration_reason=self.weak_calibration_reason,
                    speed_geometry_diagnostics=self._speed_geometry_diagnostics(
                        track,
                        contact_point,
                        plane_id=None,
                        plane_status=plane_selection.status,
                        plane_reason=plane_selection.reason,
                    ),
                )
                continue
            active_transformer = self.plane_transformers.get(
                selected_plane.plane_id,
                self.view_transformer,
            )
            self.speed_estimator.view_transformer = active_transformer
            bev_map = self.plane_bev_confidence_maps.get(
                selected_plane.plane_id,
                self.bev_confidence_map,
            )
            bev_risk = bev_map.assess(contact_point.pixel)
            self._bev_checked_count += 1
            world_position = active_transformer.transform_point(*contact_point.pixel)
            speed_geometry_diagnostics = self._speed_geometry_diagnostics(
                track,
                contact_point,
                plane_id=selected_plane.plane_id,
                plane_status=plane_selection.status,
                plane_reason=plane_selection.reason,
            )
            if not self.metric_speed_admitted:
                self.speed_estimator.suppress_measurement(
                    tracker_id=track.tracker_id,
                    pixel_point=contact_point.pixel,
                    timestamp_sec=timestamp_sec,
                    quality_label="weak_scale",
                    rejection_reason=(
                        self.metric_speed_gate_reason
                        or "metric_calibration_not_trusted"
                    ),
                    preserve_previous_speed=False,
                    measurement_source=contact_point.measurement_source,
                    measurement_confidence=contact_point.confidence,
                    local_scale_percentile=bev_risk.local_scale_percentile,
                    bev_risk_level=bev_risk.risk_level,
                    bev_risk_reason=bev_risk.risk_reason,
                    scale_confidence_label=self.scale_confidence_label,
                    weak_calibration_reason=self.weak_calibration_reason,
                    plane_id=selected_plane.plane_id,
                    speed_geometry_diagnostics=speed_geometry_diagnostics,
                )
                self.speed_estimator.annotate_record(
                    track.tracker_id,
                    contact_fusion_sources=contact_point.fusion_sources,
                    contact_fusion_weights=contact_point.fusion_weights,
                    contact_pixel_covariance=contact_point.pixel_covariance,
                    contact_fusion_confidence=contact_point.fusion_confidence,
                    contact_outlier_source=self._joined_sources(contact_point.outlier_sources),
                    contact_innovation_score=contact_point.innovation_score,
                )
                continue
            integrity = self.tracking_integrity_monitor.assess(
                track,
                world_position=world_position,
                timestamp_sec=timestamp_sec,
                previous_record=self.speed_estimator.get_record(track.tracker_id),
                active_track_ids=active_ids,
            )
            self._integrity_results[track.tracker_id] = integrity
            if integrity.id_switch_risk >= 0.75:
                self._integrity_event_count += 1
            if integrity.reset_speed_history:
                self.speed_estimator.reset_track(track.tracker_id)
            if integrity.speed_frozen:
                self._speed_frozen_count += 1
                frozen_record = self.speed_estimator.get_record(track.tracker_id)
                self.speed_estimator.annotate_record(
                    track.tracker_id,
                    tracking_integrity_state=integrity.state,
                    id_switch_risk=integrity.id_switch_risk,
                    speed_frozen=True,
                    integrity_rejection_reason=integrity.rejection_reason,
                    bev_risk_level=bev_risk.risk_level,
                    bev_risk_reason=bev_risk.risk_reason,
                    local_scale_percentile=bev_risk.local_scale_percentile,
                    contact_fusion_sources=contact_point.fusion_sources,
                    contact_fusion_weights=contact_point.fusion_weights,
                    contact_pixel_covariance=contact_point.pixel_covariance,
                    contact_fusion_confidence=contact_point.fusion_confidence,
                    contact_outlier_source=self._joined_sources(contact_point.outlier_sources),
                    contact_innovation_score=contact_point.innovation_score,
                    optical_flow_inlier_ratio=contact_point.optical_flow_inlier_ratio,
                    scale_confidence_label=self.scale_confidence_label,
                    weak_calibration_reason=self.weak_calibration_reason,
                    plane_id=selected_plane.plane_id,
                    speed_geometry_diagnostics=speed_geometry_diagnostics,
                    calibration_uncertainty_band_kmh=self._calibration_uncertainty_band(
                        frozen_record.speed_kmh if frozen_record is not None else None,
                    ),
                    calibration_speed_posterior=self._calibration_speed_posterior(
                        frozen_record,
                    ),
                    joint_speed_posterior=self._joint_speed_posterior(frozen_record),
                )
                continue

            if bev_risk.risk_level == "rejected":
                self._bev_rejected_count += 1
            measurement_confidence = contact_point.confidence
            pixel_sigma_px = contact_point.observation_sigma_px
            far_field_person = (
                track.class_id == 0
                and bev_risk.local_scale_percentile is not None
                and bev_risk.local_scale_percentile >= 0.85
            )
            fusion_sources = contact_point.fusion_sources or []
            if far_field_person and (
                contact_point.measurement_source.startswith("bbox")
                or "bbox" in fusion_sources
            ):
                self._far_field_bbox_contact_weak_count += 1
                measurement_confidence *= 0.55
                pixel_sigma_px *= 2.0
            if bev_risk.risk_level == "caution":
                measurement_confidence *= 0.65
                pixel_sigma_px *= 1.5
            elif bev_risk.risk_level == "rejected":
                measurement_confidence *= 0.25
                pixel_sigma_px *= 2.5
            if (
                track.class_id == 0
                and (
                    bev_risk.risk_level == "rejected"
                    or (
                        bev_risk.local_scale_percentile is not None
                        and bev_risk.local_scale_percentile >= 0.95
                    )
                )
            ):
                self.speed_estimator.suppress_measurement(
                    tracker_id=track.tracker_id,
                    pixel_point=contact_point.pixel,
                    timestamp_sec=timestamp_sec,
                    quality_label="geometry_invalid",
                    rejection_reason="far_field_perspective_rejected",
                    preserve_previous_speed=True,
                    measurement_source=contact_point.measurement_source,
                    measurement_confidence=measurement_confidence,
                    local_scale_percentile=bev_risk.local_scale_percentile,
                    bev_risk_level=bev_risk.risk_level,
                    bev_risk_reason=bev_risk.risk_reason,
                    scale_confidence_label=self.scale_confidence_label,
                    weak_calibration_reason=self.weak_calibration_reason,
                    plane_id=selected_plane.plane_id,
                    speed_geometry_diagnostics=speed_geometry_diagnostics,
                )
                self.speed_estimator.annotate_record(
                    track.tracker_id,
                    contact_fusion_sources=contact_point.fusion_sources,
                    contact_fusion_weights=contact_point.fusion_weights,
                    contact_pixel_covariance=contact_point.pixel_covariance,
                    contact_fusion_confidence=contact_point.fusion_confidence,
                    contact_outlier_source=self._joined_sources(contact_point.outlier_sources),
                    contact_innovation_score=contact_point.innovation_score,
                )
                continue
            if (
                far_field_person
                and bev_risk.local_scale_percentile >= 0.85
                and (contact_point.fusion_confidence or contact_point.confidence) < 0.45
            ):
                self.speed_estimator.annotate_record(
                    track.tracker_id,
                    speed_kmh=None,
                    physics_valid=False,
                    quality_label="geometry_invalid",
                    rejection_reason="far_field_bbox_contact_weak",
                    geometry_rejection_reason="far_field_bbox_contact_weak",
                    bev_risk_level=bev_risk.risk_level,
                    bev_risk_reason=bev_risk.risk_reason,
                    local_scale_percentile=bev_risk.local_scale_percentile,
                    contact_fusion_confidence=contact_point.fusion_confidence,
                )
                continue
            if self.scale_confidence_label == "weak_scale":
                measurement_confidence *= 0.65
                pixel_sigma_px *= 1.35
            if not self._bev_consistency_pass(
                tracker_id=track.tracker_id,
                class_id=track.class_id,
                world_position=world_position,
                timestamp_sec=timestamp_sec,
            ):
                self._bev_rejected_count += 1
                self.speed_estimator.annotate_record(
                    track.tracker_id,
                    speed_kmh=None,
                    physics_valid=False,
                    quality_label="geometry_invalid",
                    rejection_reason="bev_geometry_rejected",
                    geometry_rejection_reason=bev_risk.risk_reason
                    or "bev_geometry_rejected",
                    bev_risk_level=bev_risk.risk_level,
                    bev_risk_reason=bev_risk.risk_reason,
                    local_scale_percentile=bev_risk.local_scale_percentile,
                    plane_id=selected_plane.plane_id,
                    contact_source=contact_point.measurement_source,
                    speed_geometry_diagnostics=speed_geometry_diagnostics,
                )
                continue

            optical_flow = self._optical_flow_observation(
                track,
                timestamp_sec,
                frame_image,
            )
            auxiliary_confidence = optical_flow.confidence if optical_flow is not None else 0.0
            if optical_flow is not None:
                self._optical_flow_checked_count += 1
                if optical_flow.inlier_ratio < 0.55:
                    self._optical_flow_low_inlier_count += 1
                    auxiliary_confidence *= 0.35
            self.speed_estimator.update(
                track.tracker_id,
                contact_point.pixel,
                timestamp_sec,
                motion_profile=profile,
                detection_confidence=min(1.0, track.confidence * measurement_confidence),
                measurement_confidence=measurement_confidence,
                pixel_sigma_px=pixel_sigma_px,
                measurement_source=contact_point.measurement_source,
                auxiliary_velocity_mps=(
                    optical_flow.velocity_mps if optical_flow is not None else None
                ),
                auxiliary_confidence=auxiliary_confidence,
                pixel_covariance_px=contact_point.pixel_covariance,
                local_scale_percentile=bev_risk.local_scale_percentile,
                bbox_xyxy=track.xyxy,
                bbox_height_px=max(float(track.xyxy[3] - track.xyxy[1]), 1.0),
                pose_ankle_pixel=(
                    pose_contact_point.pixel if pose_contact_point is not None else None
                ),
                plane_id=selected_plane.plane_id,
                speed_geometry_diagnostics=speed_geometry_diagnostics,
            )
            latest_record = self.speed_estimator.get_record(track.tracker_id)
            if latest_record is not None:
                if (
                    latest_record.perspective_speed_inflation_detected
                    or latest_record.rejection_reason == "perspective_speed_inflation"
                ):
                    self._perspective_speed_inflation_count += 1
                if latest_record.rejection_reason == "pedestrian_physical_speed_gate":
                    self._pedestrian_physical_speed_gate_count += 1
                if latest_record.pedestrian_scale_drift_detected:
                    self._pedestrian_scale_drift_count += 1
                if latest_record.rejection_reason == "pedestrian_perspective_scale_drift":
                    self._pedestrian_speed_suppressed_count += 1
                if (
                    latest_record.height_consistency_score is not None
                    and latest_record.height_consistency_score < 0.55
                ):
                    self._bbox_height_consistency_fail_count += 1
            quality_label = (
                "weak_scale"
                if (
                    self.scale_confidence_label == "weak_scale"
                    and latest_record is not None
                    and latest_record.physics_valid
                    and latest_record.speed_kmh is not None
                )
                else latest_record.quality_label
                if latest_record is not None
                else None
            )
            self.speed_estimator.annotate_record(
                track.tracker_id,
                bev_risk_level=bev_risk.risk_level,
                bev_risk_reason=bev_risk.risk_reason,
                local_scale_percentile=bev_risk.local_scale_percentile,
                contact_fusion_sources=contact_point.fusion_sources,
                contact_fusion_weights=contact_point.fusion_weights,
                contact_pixel_covariance=contact_point.pixel_covariance,
                contact_fusion_confidence=contact_point.fusion_confidence,
                contact_outlier_source=self._joined_sources(contact_point.outlier_sources),
                contact_innovation_score=contact_point.innovation_score,
                optical_flow_inlier_ratio=(
                    optical_flow.inlier_ratio
                    if optical_flow is not None
                    else contact_point.optical_flow_inlier_ratio
                ),
                optical_flow_velocity_covariance=(
                    optical_flow.velocity_covariance
                    if optical_flow is not None
                    else None
                ),
                tracking_integrity_state=integrity.state,
                id_switch_risk=integrity.id_switch_risk,
                speed_frozen=False,
                integrity_rejection_reason=integrity.rejection_reason,
                **({"quality_label": quality_label} if quality_label is not None else {}),
                scale_confidence_label=self.scale_confidence_label,
                weak_calibration_reason=self.weak_calibration_reason,
                calibration_uncertainty_band_kmh=self._calibration_uncertainty_band(
                    latest_record.speed_kmh if latest_record is not None else None,
                ),
                calibration_speed_posterior=self._calibration_speed_posterior(
                    latest_record,
                ),
                joint_speed_posterior=self._joint_speed_posterior(latest_record),
            )
        for tracker_id in list(self._latest_contact_points):
            if tracker_id not in active_ids:
                self._latest_contact_points.pop(tracker_id, None)
        return contact_points

    def _fuse_contact_point(
        self,
        bbox_contact_point: GroundContactPoint,
        pose_contact_point: GroundContactPoint | None,
        flow_contact_point: GroundContactPoint | None,
    ) -> GroundContactPoint:
        observations = [
            ContactPointObservation(
                pixel=bbox_contact_point.pixel,
                source=bbox_contact_point.measurement_source,
                confidence=bbox_contact_point.confidence,
                sigma_px=bbox_contact_point.observation_sigma_px,
                covariance_px=bbox_contact_point.pixel_covariance,
            )
        ]
        if pose_contact_point is not None:
            observations.append(
                ContactPointObservation(
                    pixel=pose_contact_point.pixel,
                    source=pose_contact_point.measurement_source,
                    confidence=pose_contact_point.confidence,
                    sigma_px=pose_contact_point.observation_sigma_px,
                    covariance_px=pose_contact_point.pixel_covariance,
                )
            )
        if flow_contact_point is not None:
            observations.append(
                ContactPointObservation(
                    pixel=flow_contact_point.pixel,
                    source=flow_contact_point.measurement_source,
                    confidence=flow_contact_point.confidence,
                    sigma_px=flow_contact_point.observation_sigma_px,
                    covariance_px=flow_contact_point.pixel_covariance,
                    enabled=flow_contact_point.confidence >= 0.25,
                )
            )
        fused = self.contact_point_fusion.fuse(observations)
        covariance = np.asarray(fused.covariance_px, dtype=np.float64)
        sigma_px = max(0.5, float(np.trace(covariance) / 2.0) ** 0.5)
        return GroundContactPoint(
            pixel=fused.pixel,
            raw_pixel=bbox_contact_point.raw_pixel,
            confidence=fused.confidence,
            source="fused_ground_contact",
            observation_sigma_px=sigma_px,
            measurement_source="contact_point_fusion",
            fusion_sources=fused.sources,
            fusion_weights=fused.weights,
            pixel_covariance=fused.covariance_px,
            fusion_confidence=fused.confidence,
            outlier_sources=fused.outlier_sources,
            innovation_score=fused.innovation_score,
            optical_flow_inlier_ratio=(
                flow_contact_point.optical_flow_inlier_ratio
                if flow_contact_point is not None
                else None
            ),
        )

    @staticmethod
    def _joined_sources(sources: list[str] | None) -> str | None:
        return ",".join(sources) if sources else None

    @staticmethod
    def _speed_geometry_diagnostics(
        track: Track,
        contact_point: GroundContactPoint,
        *,
        plane_id: str | None,
        plane_status: str,
        plane_reason: str | None,
    ) -> dict[str, object]:
        bbox_height = max(float(track.xyxy[3] - track.xyxy[1]), 1.0)
        bbox_width = max(float(track.xyxy[2] - track.xyxy[0]), 1.0)
        aspect_ratio = bbox_width / bbox_height
        contaminated = bool(
            track.class_id == 0
            and (
                aspect_ratio > 0.85
                or contact_point.measurement_source.startswith("bbox")
                and contact_point.confidence < 0.45
            )
        )
        return {
            "plane_id": plane_id,
            "plane_status": plane_status,
            "plane_reason": plane_reason,
            "bbox_xyxy": list(track.xyxy),
            "bbox_height_px": bbox_height,
            "bbox_width_px": bbox_width,
            "bbox_aspect_ratio": aspect_ratio,
            "raw_bbox_foot": list(contact_point.raw_pixel),
            "fused_foot": list(contact_point.pixel),
            "contact_source": contact_point.measurement_source,
            "contact_covariance_px": contact_point.pixel_covariance,
            "contact_confidence": contact_point.confidence,
            "contact_fusion_confidence": contact_point.fusion_confidence,
            "contact_fusion_sources": contact_point.fusion_sources,
            "bbox_contact_contaminated": contaminated,
        }

    def _flow_refined_contact_point(
        self,
        track: Track,
        frame_image: object,
    ) -> GroundContactPoint | None:
        if self._previous_frame_image is None:
            return None
        previous_xyxy = self._previous_track_boxes.get(track.tracker_id)
        previous_contact_point = self._previous_contact_points.get(track.tracker_id)
        if previous_xyxy is None or previous_contact_point is None:
            return None
        return self.optical_flow_estimator.refine_contact_point(
            previous_frame=self._previous_frame_image,
            current_frame=frame_image,
            previous_xyxy=previous_xyxy,
            previous_contact_point=previous_contact_point,
        )

    def _bev_consistency_pass(
        self,
        tracker_id: int,
        class_id: int,
        world_position: tuple[float, float],
        timestamp_sec: float,
    ) -> bool:
        previous_record = self.speed_estimator.get_record(tracker_id)
        if (
            previous_record is None
            or previous_record.speed_kmh is None
            or not previous_record.physics_valid
            or previous_record.velocity_x_mps is None
            or previous_record.velocity_y_mps is None
        ):
            return True
        delta_t = timestamp_sec - previous_record.timestamp_sec
        if delta_t <= 0:
            return True
        predicted = (
            previous_record.world_x + previous_record.velocity_x_mps * delta_t,
            previous_record.world_y + previous_record.velocity_y_mps * delta_t,
        )
        error_m = math.dist(predicted, world_position)
        profile = self.motion_router.route_class(class_id)
        speed_mps = max((previous_record.speed_kmh or profile.nominal_speed_kmh) / 3.6, 1.0)
        gate_m = max(8.0, speed_mps * delta_t * 2.5)
        return error_m <= gate_m

    def _optical_flow_observation(
        self,
        track: Track,
        timestamp_sec: float,
        frame_image: object,
    ) -> OpticalFlowObservation | None:
        if self._previous_frame_image is None or self._previous_timestamp_sec is None:
            return None
        previous_xyxy = self._previous_track_boxes.get(track.tracker_id)
        previous_contact_point = self._previous_contact_points.get(track.tracker_id)
        if previous_xyxy is None or previous_contact_point is None:
            return None
        return self.optical_flow_estimator.estimate(
            previous_frame=self._previous_frame_image,
            current_frame=frame_image,
            previous_xyxy=previous_xyxy,
            previous_contact_point=previous_contact_point,
            delta_t_sec=timestamp_sec - self._previous_timestamp_sec,
        )

    def _flow_gap_predictions(
        self,
        tracks: list[Track],
        frame_image: object,
        frame_index: int,
    ) -> list[Track]:
        if self._previous_frame_image is None:
            return []
        active_ids = {track.tracker_id for track in tracks}
        predictions: list[Track] = []
        for tracker_id, previous_track in self._previous_track_metadata.items():
            if tracker_id in active_ids or previous_track.confidence <= 0.0:
                continue
            previous_xyxy = self._previous_track_boxes.get(tracker_id)
            previous_contact = self._previous_contact_points.get(tracker_id)
            if previous_xyxy is None or previous_contact is None:
                continue
            refined = self.optical_flow_estimator.refine_contact_point(
                previous_frame=self._previous_frame_image,
                current_frame=frame_image,
                previous_xyxy=previous_xyxy,
                previous_contact_point=previous_contact,
            )
            if refined is None or refined.confidence < 0.35:
                continue
            dx = refined.pixel[0] - previous_contact[0]
            dy = refined.pixel[1] - previous_contact[1]
            shifted_box = [
                previous_xyxy[0] + dx,
                previous_xyxy[1] + dy,
                previous_xyxy[2] + dx,
                previous_xyxy[3] + dy,
            ]
            predictions.append(
                replace(
                    previous_track,
                    xyxy=shifted_box,
                    confidence=0.0,
                    last_seen_frame=frame_index,
                    quality_label="flow_gap_prediction",
                    physics_valid=False,
                    reconstructed=True,
                )
            )
        return predictions

    def _remember_optical_flow_state(
        self,
        tracks: list[Track],
        contact_points: dict[int, GroundContactPoint],
        frame_image: object,
        timestamp_sec: float,
    ) -> None:
        self._previous_frame_image = frame_image
        self._previous_timestamp_sec = timestamp_sec
        self._previous_track_boxes = {
            track.tracker_id: list(track.xyxy)
            for track in tracks
        }
        self._previous_contact_points = {
            tracker_id: contact.pixel
            for tracker_id, contact in contact_points.items()
        }
        self._previous_track_metadata = {track.tracker_id: track for track in tracks}

    def _build_traffic_flow(
        self,
        tracks: list[Track],
        speed_records: dict[int, SpeedRecord],
        timestamp_sec: float,
    ) -> dict[str, object]:
        active_track_ids = {track.tracker_id for track in tracks}
        speeds = [
            record.speed_kmh
            for tracker_id, record in speed_records.items()
            if tracker_id in active_track_ids
            and record.physics_valid
            and record.speed_kmh is not None
        ]
        vehicle_count = sum(
            1 for track in tracks if track.class_id in self.motion_router.VEHICLE_CLASS_IDS
        )
        return self.traffic_flow.analyze(
            TrafficFlowInput(
                vehicle_count=vehicle_count,
                segment_length_m=self.segment_length_m,
                mean_speed_kmh=sum(speeds) / len(speeds) if speeds else None,
                observation_window_sec=max(timestamp_sec, 1.0),
            )
        ).to_dict()

    def _build_regional_people_count(self, tracks: list[Track]) -> dict[str, object]:
        people_tracks = [track for track in tracks if track.class_id == 0]
        points_m = [
            self.speed_estimator.view_transformer.transform_point(
                *self._latest_contact_points.get(
                    track.tracker_id,
                    GroundContactPoint(
                        pixel=track.bottom_center,
                        raw_pixel=track.bottom_center,
                        confidence=1.0,
                        source="bbox_ground_contact",
                    ),
                ).pixel
            )
            for track in people_tracks
        ]
        density_region = self._primary_profile_zone_name("pedestrian_density") or self.zone.name
        visible_area_sqm, visible_area_source = self._density_region_area_sqm(density_region)
        return self.crowd_density.analyze(
            CrowdDensityInput(
                points_m=points_m,
                region_name=density_region,
                region_width_m=self.segment_width_m,
                region_length_m=self.segment_length_m,
                direct_detection_count=len(people_tracks),
                visible_area_sqm=visible_area_sqm,
                visible_area_source=visible_area_source,
            )
        ).to_dict()

    def _build_infrastructure_semantics(
        self,
        tracks: list[Track],
        frame_image: object,
    ) -> dict[str, object]:
        traffic_light_tracks = [
            track for track in tracks if track.class_id == 9
        ]
        stop_sign_tracks = [
            track for track in tracks if track.class_id == 11
        ]
        vehicle_tracks = [
            track for track in tracks if track.class_id in self.motion_router.VEHICLE_CLASS_IDS
        ]
        traffic_light_states: list[dict[str, object]] = [
            {
                "tracker_id": track.tracker_id,
                **self.signal_state_estimator.estimate(frame_image, track.xyxy).to_dict(),
            }
            for track in traffic_light_tracks
        ]
        raw_traffic_light_state = self._aggregate_signal_state(traffic_light_states)
        traffic_light_state, traffic_light_state_source = self._resolve_signal_state(
            raw_traffic_light_state,
            has_traffic_light=bool(traffic_light_tracks),
        )
        red_light_violation_track_ids = (
            [
                track.tracker_id
                for track in vehicle_tracks
                if self._crossed_zone_line(track.tracker_id)
            ]
            if traffic_light_state == "red"
            else []
        )
        return {
            "traffic_light_count": len(traffic_light_tracks),
            "stop_sign_count": len(stop_sign_tracks),
            "traffic_light_state": traffic_light_state,
            "traffic_light_state_source": traffic_light_state_source,
            "traffic_light_states": traffic_light_states,
            "configured_traffic_light_rois": self.calibration_context.get(
                "profile_traffic_light_rois",
                [],
            ),
            "violation_on_crosswalk": bool(red_light_violation_track_ids),
            "red_light_violation_candidate_track_ids": red_light_violation_track_ids,
            "dynamic_vehicle_count": len(vehicle_tracks),
            "semantic_note": (
                "YOLO infrastructure detections are routed to a local ROI color rule; "
                "red-light risk combines signal state with vehicle stop-line crossing."
            ),
            "model_reference": "Model 10 infrastructure routing",
        }

    def _build_safety_metrics(
        self,
        tracks: list[Track],
        speed_records: dict[int, SpeedRecord],
        infrastructure_semantics: dict[str, object],
    ) -> dict[str, object]:
        vehicle_records = [
            speed_records[track.tracker_id]
            for track in tracks
            if track.class_id in self.motion_router.VEHICLE_CLASS_IDS
            and track.tracker_id in speed_records
            and speed_records[track.tracker_id].physics_valid
            and speed_records[track.tracker_id].speed_kmh is not None
        ]
        min_headway_sec: float | None = None
        min_ttc_sec: float | None = None
        for index, ego in enumerate(vehicle_records):
            ego_speed_kmh = ego.speed_kmh
            if ego_speed_kmh is None:
                continue
            for other in vehicle_records[index + 1 :]:
                other_speed_kmh = other.speed_kmh
                if other_speed_kmh is None:
                    continue
                distance_m = (
                    (ego.world_x - other.world_x) ** 2
                    + (ego.world_y - other.world_y) ** 2
                ) ** 0.5
                ego_speed_mps = max(ego_speed_kmh / 3.6, 1e-6)
                headway_sec = distance_m / ego_speed_mps
                min_headway_sec = (
                    headway_sec
                    if min_headway_sec is None
                    else min(min_headway_sec, headway_sec)
                )
                relative_speed_mps = abs(ego_speed_kmh - other_speed_kmh) / 3.6
                if relative_speed_mps > 1e-6:
                    ttc_sec = distance_m / relative_speed_mps
                    min_ttc_sec = ttc_sec if min_ttc_sec is None else min(min_ttc_sec, ttc_sec)
        speed_limit_kmh = self._profile_speed_limit_kmh()
        speeding_track_ids: list[int] = []
        for track in tracks:
            record = speed_records.get(track.tracker_id)
            if (
                track.class_id in self.motion_router.VEHICLE_CLASS_IDS
                and record is not None
                and record.physics_valid
                and record.speed_kmh is not None
                and record.speed_kmh >= speed_limit_kmh
            ):
                speeding_track_ids.append(track.tracker_id)
        red_light_candidates = infrastructure_semantics.get(
            "red_light_violation_candidate_track_ids",
            [],
        )
        if not isinstance(red_light_candidates, Iterable) or isinstance(
            red_light_candidates,
            (str, bytes),
        ):
            red_light_candidates = []
        red_light_violation_track_ids = [
            int(track_id)
            for track_id in red_light_candidates
        ]
        return {
            "vehicle_pair_count": max(
                0,
                len(vehicle_records) * (len(vehicle_records) - 1) // 2,
            ),
            "min_time_headway_sec": min_headway_sec,
            "min_time_to_collision_sec": min_ttc_sec,
            "speed_limit_kmh": speed_limit_kmh,
            "speeding_track_ids": speeding_track_ids,
            "red_light_violation_track_ids": red_light_violation_track_ids,
            "configured_polygon_zones": self.calibration_context.get(
                "profile_polygon_zones",
                [],
            ),
            "configured_risk_areas": self.calibration_context.get("profile_risk_areas", []),
            "rule_source": (
                "camera_profile_rules"
                if self.calibration_context.get("camera_profile_id")
                else "default_runtime_rules"
            ),
            "risk_level": self._risk_level(
                min_headway_sec,
                min_ttc_sec,
                speeding_track_ids,
                red_light_violation_track_ids,
            ),
            "model_reference": "trajectory geometry + relative speed safety surrogate",
        }

    def _build_integrity_diagnostics(self) -> dict[str, object]:
        checked = max(self._bev_checked_count, 1)
        fusion_count = max(self._contact_fusion_count, 1)
        state_counts: dict[str, int] = {}
        for result in self._integrity_results.values():
            state_counts[result.state] = state_counts.get(result.state, 0) + 1
        diagnostics = {
            "tracking_integrity_state_counts": state_counts,
            "id_switch_risk_count": self._integrity_event_count,
            "speed_frozen_count": self._speed_frozen_count,
            "speed_frozen_ratio": self._speed_frozen_count / checked,
            "bev_checked_count": self._bev_checked_count,
            "bev_rejected_count": self._bev_rejected_count,
            "bev_rejected_ratio": self._bev_rejected_count / checked,
            "contact_fusion_count": self._contact_fusion_count,
            "contact_fusion_low_confidence_count": (
                self._contact_fusion_low_confidence_count
            ),
            "contact_fusion_low_confidence_ratio": (
                self._contact_fusion_low_confidence_count / fusion_count
            ),
            "contact_outlier_count": self._contact_outlier_count,
            "contact_outlier_ratio": self._contact_outlier_count / fusion_count,
            "optical_flow_checked_count": self._optical_flow_checked_count,
            "optical_flow_low_inlier_count": self._optical_flow_low_inlier_count,
            "optical_flow_low_inlier_ratio": (
                self._optical_flow_low_inlier_count
                / max(self._optical_flow_checked_count, 1)
            ),
            "weak_scale_mode": self.scale_confidence_label == "weak_scale",
            "model_reference": "bev_confidence_map + contact_fusion + tracking_integrity_monitor",
        }
        diagnostics.update(self._tracking_diagnostics)
        return diagnostics

    def _build_speed_geometry_diagnostics(self) -> dict[str, object]:
        return {
            "perspective_speed_inflation_count": self._perspective_speed_inflation_count,
            "pedestrian_physical_speed_gate_count": (
                self._pedestrian_physical_speed_gate_count
            ),
            "far_field_bbox_contact_weak_count": self._far_field_bbox_contact_weak_count,
            "pedestrian_scale_drift_count": self._pedestrian_scale_drift_count,
            "pedestrian_speed_suppressed_count": self._pedestrian_speed_suppressed_count,
            "pose_geometry_used_count": self._pose_geometry_used_count,
            "bbox_height_consistency_fail_count": (
                self._bbox_height_consistency_fail_count
            ),
            "model_reference": "pedestrian_perspective_geometry_guard_v1",
        }

    def _adapter_tracking_diagnostics(self) -> dict[str, object]:
        diagnostics = getattr(self.adapter, "diagnostics_dict", None)
        if callable(diagnostics):
            value = diagnostics()
            return dict(value) if isinstance(value, dict) else {}
        diagnostics_value = getattr(self.adapter, "diagnostics", None)
        to_dict = getattr(diagnostics_value, "to_dict", None)
        if callable(to_dict):
            value = to_dict()
            return dict(value) if isinstance(value, dict) else {}
        return {}

    def _profile_speed_limit_kmh(self) -> float:
        tuning = self.calibration_context.get("profile_tuning")
        if isinstance(tuning, dict):
            value = tuning.get("speed_limit_kmh")
            if isinstance(value, (int, float)) and value > 0:
                return float(value)
        return 60.0

    def _primary_profile_zone_name(self, kind: str) -> str | None:
        zones = self.calibration_context.get("profile_polygon_zones")
        if not isinstance(zones, list):
            return None
        for zone in zones:
            if not isinstance(zone, dict):
                continue
            zone_name = zone.get("name")
            if isinstance(zone_name, str) and kind in zone_name:
                return zone_name
        return None

    def _density_region_area_sqm(self, region_name: str) -> tuple[float | None, str]:
        zone = self._profile_zone(region_name)
        if zone is None:
            return None, "full_region_rect"
        points = self._points_from_world(zone.get("points_world"))
        if points is None:
            points = self._points_from_ratio(
                zone.get("points_ratio"),
                self.segment_width_m,
                self.segment_length_m,
            )
        if points is None:
            return None, "full_region_rect"
        area = self._polygon_area_sqm(points)
        if area <= 1e-6 or not math.isfinite(area):
            return None, "full_region_rect"
        return area, "configured_roi_polygon"

    def _profile_zone(self, name: str) -> dict[str, object] | None:
        zones = self.calibration_context.get("profile_polygon_zones")
        if not isinstance(zones, list):
            return None
        for zone in zones:
            if not isinstance(zone, dict):
                continue
            if zone.get("name") == name:
                return cast(dict[str, object], zone)
        return None

    @staticmethod
    def _points_from_world(value: object) -> list[tuple[float, float]] | None:
        if not isinstance(value, list):
            return None
        points: list[tuple[float, float]] = []
        for point in value:
            if not isinstance(point, (list, tuple)) or len(point) != 2:
                return None
            try:
                points.append((float(point[0]), float(point[1])))
            except (TypeError, ValueError):
                return None
        return points if len(points) >= 3 else None

    @staticmethod
    def _points_from_ratio(
        value: object,
        width_m: float,
        length_m: float,
    ) -> list[tuple[float, float]] | None:
        if not isinstance(value, list):
            return None
        points: list[tuple[float, float]] = []
        for point in value:
            if not isinstance(point, (list, tuple)) or len(point) != 2:
                return None
            try:
                points.append((float(point[0]) * width_m, float(point[1]) * length_m))
            except (TypeError, ValueError):
                return None
        return points if len(points) >= 3 else None

    @staticmethod
    def _polygon_area_sqm(points: list[tuple[float, float]]) -> float:
        area = 0.0
        for index, (x1, y1) in enumerate(points):
            x2, y2 = points[(index + 1) % len(points)]
            area += x1 * y2 - x2 * y1
        return abs(area) * 0.5

    def _update_pixel_histories(self, tracks: list[Track]) -> None:
        active_ids = {track.tracker_id for track in tracks}
        for track in tracks:
            history = self._pixel_histories.setdefault(track.tracker_id, [])
            history.append(track.bottom_center)
            self._pixel_histories[track.tracker_id] = history[-12:]
        for tracker_id in list(self._pixel_histories):
            if tracker_id not in active_ids:
                self._pixel_histories[tracker_id] = self._pixel_histories[tracker_id][-4:]

    @staticmethod
    def _aggregate_signal_state(signal_states: list[dict[str, object]]) -> str:
        known_states = [
            state
            for state in signal_states
            if state.get("state") in {"red", "yellow", "green"}
        ]
        if not known_states:
            return "unknown"
        priority = {"red": 3, "yellow": 2, "green": 1}
        strongest = max(
            known_states,
            key=lambda item: (
                priority[str(item["state"])],
                float(cast(float | int | str, item.get("confidence", 0.0))),
            ),
        )
        return str(strongest["state"])

    def _resolve_signal_state(
        self,
        raw_state: str,
        has_traffic_light: bool,
    ) -> tuple[str, str]:
        if raw_state in {"red", "yellow", "green"}:
            self._last_reliable_signal_state = raw_state
            return raw_state, "roi_color_rule"
        if has_traffic_light and self._last_reliable_signal_state != "unknown":
            return self._last_reliable_signal_state, "last_reliable_roi_color_rule"
        return "unknown", "unresolved_roi_color_rule" if has_traffic_light else "no_signal"

    def _crossed_zone_line(self, tracker_id: int) -> bool:
        history = self._pixel_histories.get(tracker_id, [])
        if len(history) < 2:
            return False
        previous_side = self._line_side(history[-2])
        current_side = self._line_side(history[-1])
        if abs(current_side) <= self._stop_line_tolerance_px():
            return True
        return previous_side * current_side < 0.0

    def _line_side(self, point: tuple[float, float]) -> float:
        x1, y1 = float(self.zone.line_start[0]), float(self.zone.line_start[1])
        x2, y2 = float(self.zone.line_end[0]), float(self.zone.line_end[1])
        px, py = point
        return (x2 - x1) * (py - y1) - (y2 - y1) * (px - x1)

    def _stop_line_tolerance_px(self) -> float:
        x1, y1 = float(self.zone.line_start[0]), float(self.zone.line_start[1])
        x2, y2 = float(self.zone.line_end[0]), float(self.zone.line_end[1])
        return max(((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5 * 0.025, 2.0)

    @staticmethod
    def _risk_level(
        min_headway_sec: float | None,
        min_ttc_sec: float | None,
        speeding_track_ids: list[int],
        red_light_violation_track_ids: list[int],
    ) -> str:
        if red_light_violation_track_ids:
            return "critical"
        if min_ttc_sec is not None and min_ttc_sec < 2.0:
            return "critical"
        if speeding_track_ids:
            return "elevated"
        if min_headway_sec is not None and min_headway_sec < 1.5:
            return "elevated"
        return "nominal"
