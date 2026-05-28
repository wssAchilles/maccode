from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from domain.detection.models import Detection, Detections
from domain.reports.generators import ReportGenerator
from domain.speed.estimator import SpeedEstimator
from domain.speed.view_transformer import ViewTransformer
from domain.tracking.service import TrackingService
from domain.zones.models import ZoneConfig
from domain.zones.service import ZoneService


def generate_demo_report() -> dict[str, Any]:
    tracker = TrackingService(iou_threshold=0.2)
    zone_service = ZoneService([ZoneConfig("main_gate", [0, 10], [80, 10])])
    transformer = ViewTransformer(np.array([[0.1, 0, 0], [0, 0.1, 0], [0, 0, 1]], dtype=float))
    speed_estimator = SpeedEstimator(transformer, smoothing_window=3, min_displacement_m=0.01)
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
            )
            for track in tracks
        }
        latest_report = reports.add_frame(
            frame_index=detections.frame_index,
            timestamp_sec=detections.timestamp_sec,
            tracks=tracks,
            zone_stats=stats,
            fps=24.0,
            speeds=speeds,
        )

    if latest_report is None:
        raise RuntimeError("demo produced no frame report")
    return latest_report.to_dict()


if __name__ == "__main__":
    print(json.dumps(generate_demo_report(), ensure_ascii=False, indent=2))
