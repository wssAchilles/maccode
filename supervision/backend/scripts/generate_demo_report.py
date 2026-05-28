from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from domain.calibration.models import CalibrationPoint
from domain.calibration.service import CalibrationService
from domain.detection.models import Detection, Detections
from domain.motion.router import MotionRouter
from domain.reports.generators import ReportGenerator
from domain.speed.estimator import SpeedEstimator
from domain.speed.view_transformer import ViewTransformer
from domain.tracking.service import TrackingService
from domain.traffic_flow.models import TrafficFlowInput
from domain.traffic_flow.service import TrafficFlowService
from domain.zones.models import ZoneConfig
from domain.zones.service import ZoneService


def generate_demo_report() -> dict[str, Any]:
    tracker = TrackingService(iou_threshold=0.2)
    zone_service = ZoneService([ZoneConfig("main_gate", [0, 10], [80, 10])])
    calibration = CalibrationService().compute_homography_ransac(
        [
            CalibrationPoint(0, 0, 0, 0),
            CalibrationPoint(100, 0, 10, 0),
            CalibrationPoint(100, 100, 10, 10),
            CalibrationPoint(0, 100, 0, 10),
            CalibrationPoint(50, 0, 5, 0),
            CalibrationPoint(50, 100, 5, 10),
        ],
        random_seed=3,
    )
    transformer = ViewTransformer(calibration.homography_matrix)
    speed_estimator = SpeedEstimator(
        transformer,
        smoothing_window=3,
        min_displacement_m=0.01,
        position_rmse_m=max(calibration.reprojection_rmse, 0.05),
        timestamp_uncertainty_sec=1.0 / 24.0,
    )
    motion_router = MotionRouter()
    traffic_flow = TrafficFlowService(free_flow_speed_kmh=40.0, jam_density_veh_per_km=100.0)
    reports = ReportGenerator()

    frames = [
        Detections([Detection([10, 0, 30, 8], 0.92, 2, "car")], 1, 0.0),
        Detections([Detection([20, 2, 40, 9], 0.90, 2, "car")], 2, 1.0),
        Detections([Detection([30, 12, 50, 24], 0.89, 2, "car")], 3, 2.0),
    ]

    latest_report = None
    for detections in frames:
        tracks = tracker.update(detections)
        stats = zone_service.trigger(tracks)
        speeds = {
            track.tracker_id: speed_estimator.update(
                track.tracker_id,
                track.bottom_center,
                detections.timestamp_sec,
                process_noise=motion_router.route_class(track.class_id).process_noise,
            )
            for track in tracks
        }
        speed_records = speed_estimator.get_all_records()
        valid_speeds = [record.speed_kmh for record in speed_records.values()]
        traffic_flow_result = traffic_flow.analyze(
            TrafficFlowInput(
                vehicle_count=len([track for track in tracks if track.class_id in {2, 5, 7}]),
                segment_length_m=500.0,
                mean_speed_kmh=sum(valid_speeds) / len(valid_speeds) if valid_speeds else None,
                observation_window_sec=max(detections.timestamp_sec, 1.0),
            )
        )
        latest_report = reports.add_frame(
            frame_index=detections.frame_index,
            timestamp_sec=detections.timestamp_sec,
            tracks=tracks,
            zone_stats=stats,
            fps=24.0,
            speeds=speeds,
            speed_records=speed_records,
            calibration_quality=calibration.calibration_quality,
            traffic_flow=traffic_flow_result.to_dict(),
        )

    if latest_report is None:
        raise RuntimeError("demo produced no frame report")
    return latest_report.to_dict()


if __name__ == "__main__":
    print(json.dumps(generate_demo_report(), ensure_ascii=False, indent=2))
