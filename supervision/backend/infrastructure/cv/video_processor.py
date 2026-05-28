from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Protocol

from domain.calibration.models import HomographyResult
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
        segment_length_m: float = 500.0,
        position_rmse_floor_m: float = 0.05,
    ) -> None:
        self.detector = detector
        self.adapter = adapter
        self.calibration = calibration
        self.zone = zone
        self.fps = fps
        self.segment_length_m = segment_length_m
        self.motion_router = MotionRouter()
        self.speed_estimator = SpeedEstimator(
            ViewTransformer(calibration.homography_matrix),
            position_rmse_m=max(calibration.reprojection_rmse, position_rmse_floor_m),
            timestamp_uncertainty_sec=1.0 / fps,
        )
        self.report_generator = ReportGenerator()
        self.traffic_flow = TrafficFlowService(
            free_flow_speed_kmh=40.0,
            jam_density_veh_per_km=100.0,
        )

    def process_frames(self, frames: Iterable[VideoFrame]) -> dict[str, Any]:
        latest_report: dict[str, Any] | None = None
        for frame in frames:
            detections = self.detector.detect(frame.image, frame.frame_index, frame.timestamp_sec)
            adapter_result = self.adapter.track_and_count(
                detections,
                line_start=(float(self.zone.line_start[0]), float(self.zone.line_start[1])),
                line_end=(float(self.zone.line_end[0]), float(self.zone.line_end[1])),
                zone_name=self.zone.name,
            )
            tracks = list(adapter_result.tracks)
            self._update_track_speeds(tracks, frame.timestamp_sec)
            speed_records = self.speed_estimator.get_all_records()
            flow = self._build_traffic_flow(tracks, speed_records, frame.timestamp_sec)
            regional_people_count = self._build_regional_people_count(tracks)
            infrastructure_semantics = self._build_infrastructure_semantics(tracks)
            safety_metrics = self._build_safety_metrics(tracks, speed_records)
            report = self.report_generator.add_frame(
                frame_index=frame.frame_index,
                timestamp_sec=frame.timestamp_sec,
                tracks=tracks,
                zone_stats=[adapter_result.zone_stats],
                fps=self.fps,
                speed_records=speed_records,
                calibration_quality=self.calibration.calibration_quality,
                traffic_flow=flow,
                regional_people_count=regional_people_count,
                infrastructure_semantics=infrastructure_semantics,
                safety_metrics=safety_metrics,
            )
            latest_report = report.to_dict()

        if latest_report is None:
            raise ValueError("no frames were processed")
        return latest_report

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
        people_count = sum(1 for track in tracks if track.class_id == 0)
        return {
            "region_name": self.zone.name,
            "people_count": people_count,
            "unit": "person",
            "estimation_method": (
                "density_integral_fallback" if people_count >= 30 else "direct_detection_count"
            ),
            "density_integral_triggered": people_count >= 30,
            "model_reference": "Model 9 + Model 10 fallback policy",
        }

    def _build_infrastructure_semantics(self, tracks: list[Track]) -> dict[str, object]:
        traffic_light_tracks = [
            track for track in tracks if track.class_id == 9
        ]
        stop_sign_tracks = [
            track for track in tracks if track.class_id == 11
        ]
        vehicle_tracks = [
            track for track in tracks if track.class_id in self.motion_router.VEHICLE_CLASS_IDS
        ]
        return {
            "traffic_light_count": len(traffic_light_tracks),
            "stop_sign_count": len(stop_sign_tracks),
            "traffic_light_state": "unknown",
            "violation_on_crosswalk": False,
            "dynamic_vehicle_count": len(vehicle_tracks),
            "semantic_note": (
                "YOLO class semantics are extracted locally; red/green state requires "
                "a dedicated signal-state classifier or manual ROI rule."
            ),
            "model_reference": "Model 10 infrastructure routing",
        }

    def _build_safety_metrics(
        self,
        tracks: list[Track],
        speed_records: dict[int, SpeedRecord],
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
        return {
            "vehicle_pair_count": max(0, len(vehicle_ids) * (len(vehicle_ids) - 1) // 2),
            "min_time_headway_sec": min_headway_sec,
            "min_time_to_collision_sec": min_ttc_sec,
            "risk_level": self._risk_level(min_headway_sec, min_ttc_sec),
            "model_reference": "trajectory geometry + relative speed safety surrogate",
        }

    @staticmethod
    def _risk_level(
        min_headway_sec: float | None,
        min_ttc_sec: float | None,
    ) -> str:
        if min_ttc_sec is not None and min_ttc_sec < 2.0:
            return "critical"
        if min_headway_sec is not None and min_headway_sec < 1.5:
            return "elevated"
        return "nominal"
