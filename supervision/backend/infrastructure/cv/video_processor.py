from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, cast

from domain.calibration.models import HomographyResult
from domain.calibration.service import CalibrationService
from domain.crowd_density.models import CrowdDensityInput
from domain.crowd_density.service import CrowdDensityService
from domain.detection.models import Detections
from domain.motion.router import MotionRouter
from domain.reports.generators import ReportGenerator
from domain.speed.estimator import SpeedEstimator
from domain.speed.models import SpeedRecord
from domain.speed.view_transformer import ViewTransformer
from domain.tracking.models import Track
from domain.traffic_flow.models import TrafficFlowInput
from domain.traffic_flow.service import TrafficFlowService
from domain.zones.models import ZoneConfig

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
    ) -> None:
        self.detector = detector
        self.adapter = adapter
        self.calibration = calibration
        self.zone = zone
        self.fps = fps
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.segment_width_m = segment_width_m
        self.segment_length_m = segment_length_m
        self.grid_spacing_m = grid_spacing_m
        self.calibration_context = calibration_context or {}
        self.motion_router = MotionRouter()
        self.speed_estimator = SpeedEstimator(
            ViewTransformer(calibration.homography_matrix),
            position_rmse_m=max(calibration.reprojection_rmse, position_rmse_floor_m),
            timestamp_uncertainty_sec=1.0 / fps,
        )
        self.report_generator = ReportGenerator()
        self.crowd_density = CrowdDensityService()
        self.signal_state_estimator = TrafficLightStateEstimator()
        self.traffic_flow = TrafficFlowService(
            free_flow_speed_kmh=40.0,
            jam_density_veh_per_km=100.0,
        )
        self.homography_grid = CalibrationService().build_homography_grid(
            calibration,
            frame_width=frame_width,
            frame_height=frame_height,
            world_width_m=segment_width_m,
            world_length_m=segment_length_m,
            spacing_m=grid_spacing_m,
        ).to_dict()
        self.frame_reports: list[dict[str, Any]] = []
        self._pixel_histories: dict[int, list[tuple[float, float]]] = {}
        self._last_reliable_signal_state = "unknown"
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
                tracks = list(adapter_result.tracks)
                self._update_pixel_histories(tracks)
                self._update_track_speeds(tracks, frame.timestamp_sec)
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
                    zone_stats=[adapter_result.zone_stats],
                    fps=self.fps,
                    speed_records=speed_records,
                    calibration_quality=self.calibration.calibration_quality,
                    calibration_diagnostics=self._build_calibration_diagnostics(),
                    homography_grid=self.homography_grid,
                    traffic_flow=flow,
                    regional_people_count=regional_people_count,
                    infrastructure_semantics=infrastructure_semantics,
                    safety_metrics=safety_metrics,
                )
                latest_report = report.to_dict()
                self.frame_reports.append(latest_report)
                if self._renderer is not None:
                    self._renderer.render(frame.image, latest_report)
        finally:
            if self._renderer is not None:
                self._renderer.close()

        if latest_report is None:
            raise ValueError("no frames were processed")
        return latest_report

    def _build_calibration_diagnostics(self) -> dict[str, object]:
        return {
            "homography_model": "RANSAC planar homography, pixel(u,v) -> ground(X,Y)",
            "calibration_source": self.calibration_context.get("calibration_source"),
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
            "reprojection_rmse_px": self.calibration.reprojection_rmse,
            "inlier_count": self.calibration.inlier_count,
            "condition_number": self.calibration.condition_number,
            "position_rmse_m": self.speed_estimator.position_rmse_m,
            "timestamp_uncertainty_sec": self.speed_estimator.timestamp_uncertainty_sec,
            "error_sources": [
                "homography calibration residual",
                "detector bounding-box jitter",
                "frame timestamp quantization",
                "perspective extrapolation outside calibrated road plane",
            ],
            "model_reference": "Model 1 + Model 3 + Model 6 + Model 10",
        }

    def _update_track_speeds(self, tracks: list[Track], timestamp_sec: float) -> None:
        for track in tracks:
            profile = self.motion_router.route_class(track.class_id)
            if not profile.should_estimate_speed:
                continue
            self.speed_estimator.update(
                track.tracker_id,
                track.bottom_center,
                timestamp_sec,
                process_noise=profile.process_noise,
            )

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
            self.speed_estimator.view_transformer.transform_point(*track.bottom_center)
            for track in people_tracks
        ]
        density_region = self._primary_profile_zone_name("pedestrian_density") or self.zone.name
        return self.crowd_density.analyze(
            CrowdDensityInput(
                points_m=points_m,
                region_name=density_region,
                region_width_m=self.segment_width_m,
                region_length_m=self.segment_length_m,
                direct_detection_count=len(people_tracks),
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
        vehicle_ids = [
            track.tracker_id
            for track in tracks
            if track.class_id in self.motion_router.VEHICLE_CLASS_IDS
            and track.tracker_id in speed_records
        ]
        min_headway_sec: float | None = None
        min_ttc_sec: float | None = None
        for index, ego_id in enumerate(vehicle_ids):
            ego = speed_records[ego_id]
            for other_id in vehicle_ids[index + 1 :]:
                other = speed_records[other_id]
                distance_m = (
                    (ego.world_x - other.world_x) ** 2
                    + (ego.world_y - other.world_y) ** 2
                ) ** 0.5
                ego_speed_mps = max(ego.speed_kmh / 3.6, 1e-6)
                headway_sec = distance_m / ego_speed_mps
                min_headway_sec = (
                    headway_sec
                    if min_headway_sec is None
                    else min(min_headway_sec, headway_sec)
                )
                relative_speed_mps = abs(ego.speed_kmh - other.speed_kmh) / 3.6
                if relative_speed_mps > 1e-6:
                    ttc_sec = distance_m / relative_speed_mps
                    min_ttc_sec = ttc_sec if min_ttc_sec is None else min(min_ttc_sec, ttc_sec)
        speed_limit_kmh = self._profile_speed_limit_kmh()
        speeding_track_ids = [
            track.tracker_id
            for track in tracks
            if track.class_id in self.motion_router.VEHICLE_CLASS_IDS
            and (speed_records.get(track.tracker_id) is not None)
            and speed_records[track.tracker_id].speed_kmh >= speed_limit_kmh
        ]
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
            "vehicle_pair_count": max(0, len(vehicle_ids) * (len(vehicle_ids) - 1) // 2),
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
