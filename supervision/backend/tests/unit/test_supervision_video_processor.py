from __future__ import annotations

import numpy as np
from domain.calibration.models import CalibrationPoint
from domain.calibration.service import CalibrationService
from domain.detection.models import Detection, Detections
from domain.speed.models import SpeedRecord
from domain.zones.models import ZoneConfig, ZoneStats
from infrastructure.cv.video_processor import SupervisionVideoProcessor, VideoFrame


class FakeDetector:
    def detect(self, _frame: object, frame_index: int, timestamp_sec: float) -> Detections:
        x1 = 10.0 + frame_index * 10.0
        return Detections(
            items=[Detection([x1, 0.0, x1 + 20.0, 10.0], 0.9, 2, "car")],
            frame_index=frame_index,
            timestamp_sec=timestamp_sec,
        )


class FakeAdapter:
    def track_and_count(
        self,
        detections: Detections,
        line_start: tuple[float, float],
        line_end: tuple[float, float],
        zone_name: str = "main_gate",
    ) -> object:
        detection = detections.items[0]
        return type(
            "AdapterResult",
            (),
            {
                "tracks": [detection.to_track(1, detections.frame_index)],
                "zone_stats": ZoneStats(zone_name, in_count=1, out_count=0),
            },
        )()


def test_supervision_video_processor_generates_math_enriched_frame_report() -> None:
    calibration = CalibrationService().compute_homography(
        [
            CalibrationPoint(0, 0, 0, 0),
            CalibrationPoint(100, 0, 10, 0),
            CalibrationPoint(100, 100, 10, 10),
            CalibrationPoint(0, 100, 0, 10),
        ]
    )
    frames = [
        VideoFrame(np.zeros((8, 8, 3), dtype=np.uint8), frame_index=1, timestamp_sec=0.0),
        VideoFrame(np.zeros((8, 8, 3), dtype=np.uint8), frame_index=2, timestamp_sec=1.0),
        VideoFrame(np.zeros((8, 8, 3), dtype=np.uint8), frame_index=3, timestamp_sec=2.0),
    ]

    report = SupervisionVideoProcessor(
        detector=FakeDetector(),
        adapter=FakeAdapter(),
        calibration=calibration,
        zone=ZoneConfig("main_gate", [0, 5], [100, 5]),
        fps=24.0,
    ).process_frames(frames)

    assert report["active_tracks"][0]["speed_kmh"] is not None
    assert report["active_tracks"][0]["speed_confidence"] is not None
    assert report["active_tracks"][0]["speed_confidence_interval_kmh"] is not None
    assert report["active_tracks"][0]["ground_x_m"] is not None
    assert report["active_tracks"][0]["ground_y_m"] is not None
    assert report["active_tracks"][0]["velocity_x_mps"] is not None
    assert report["active_tracks"][0]["velocity_y_mps"] is not None
    assert report["active_tracks"][0]["heading_deg"] is not None
    assert report["calibration_quality"] == "excellent"
    assert report["traffic_flow"]["density_k_veh_per_km"] > 0
    assert report["regional_people_count"]["people_count"] == 0
    assert report["regional_people_count"]["estimation_method"] == "direct_detection_count"
    assert report["infrastructure_semantics"]["dynamic_vehicle_count"] == 1
    assert report["infrastructure_semantics"]["traffic_light_state"] == "unknown"
    assert report["safety_metrics"]["risk_level"] == "nominal"


def test_traffic_flow_ignores_stale_speed_records_for_inactive_tracks() -> None:
    calibration = CalibrationService().compute_homography(
        [
            CalibrationPoint(0, 0, 0, 0),
            CalibrationPoint(100, 0, 10, 0),
            CalibrationPoint(100, 100, 10, 10),
            CalibrationPoint(0, 100, 0, 10),
        ]
    )
    processor = SupervisionVideoProcessor(
        detector=FakeDetector(),
        adapter=FakeAdapter(),
        calibration=calibration,
        zone=ZoneConfig("main_gate", [0, 5], [100, 5]),
        fps=24.0,
    )

    flow = processor._build_traffic_flow(  # noqa: SLF001
        tracks=[],
        speed_records={
            99: SpeedRecord(
                tracker_id=99,
                speed_kmh=88.0,
                timestamp_sec=2.0,
                world_x=0.0,
                world_y=0.0,
            ),
        },
        timestamp_sec=2.0,
    )

    assert flow["space_mean_speed_kmh"] is None
