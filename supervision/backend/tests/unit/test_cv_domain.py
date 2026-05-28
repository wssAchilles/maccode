from __future__ import annotations

from domain.detection.models import Detection, Detections
from domain.detection.service import DetectionService
from domain.reports.generators import ReportGenerator
from domain.tracking.service import TrackingService
from domain.zones.models import ZoneConfig
from domain.zones.service import ZoneService


def test_detection_service_converts_injected_predictions() -> None:
    service = DetectionService(
        model_path="synthetic.pt",
        predictor=lambda _frame: [
            {
                "xyxy": [10, 20, 30, 40],
                "confidence": 0.91,
                "class_id": 2,
                "class_name": "car",
            },
            {
                "xyxy": [0, 0, 5, 5],
                "confidence": 0.10,
                "class_id": 9,
                "class_name": "traffic light",
            },
        ],
        confidence_threshold=0.25,
    )

    detections = service.detect(frame=object(), frame_index=7, timestamp_sec=1.4)

    assert len(detections.items) == 1
    assert detections.frame_index == 7
    assert detections.items[0].class_name == "car"


def test_tracking_service_preserves_tracker_id_for_overlapping_detection() -> None:
    tracker = TrackingService(iou_threshold=0.3)
    first = Detections(
        items=[Detection([10, 10, 30, 30], 0.9, 2, "car")],
        frame_index=1,
        timestamp_sec=0.0,
    )
    second = Detections(
        items=[Detection([12, 10, 32, 30], 0.88, 2, "car")],
        frame_index=2,
        timestamp_sec=0.1,
    )

    first_tracks = tracker.update(first)
    second_tracks = tracker.update(second)

    assert first_tracks[0].tracker_id == second_tracks[0].tracker_id
    assert second_tracks[0].last_seen_frame == 2


def test_zone_service_counts_directional_line_crossing() -> None:
    tracker = TrackingService(iou_threshold=0.3)
    zone_service = ZoneService([ZoneConfig("main_gate", [0, 10], [40, 10])])

    frame_1 = Detections(
        items=[Detection([10, 0, 20, 8], 0.9, 2, "car")],
        frame_index=1,
        timestamp_sec=0.0,
    )
    frame_2 = Detections(
        items=[Detection([10, 12, 20, 24], 0.9, 2, "car")],
        frame_index=2,
        timestamp_sec=0.1,
    )

    zone_service.trigger(tracker.update(frame_1))
    stats = zone_service.trigger(tracker.update(frame_2))

    assert stats[0].name == "main_gate"
    assert stats[0].in_count == 1
    assert stats[0].out_count == 0


def test_report_generator_builds_frame_and_cumulative_stats() -> None:
    generator = ReportGenerator()
    tracks = [Detection([10, 10, 30, 30], 0.9, 2, "car").to_track(tracker_id=1)]
    zone_service = ZoneService([ZoneConfig("main_gate", [0, 10], [40, 10])])

    report = generator.add_frame(
        frame_index=10,
        timestamp_sec=1.0,
        tracks=tracks,
        zone_stats=zone_service.get_stats(),
        fps=24.0,
        speeds={1: 42.5},
    )
    cumulative = generator.generate_cumulative_stats()

    assert report.active_tracks[0].speed_kmh == 42.5
    assert report.active_tracks[0].speed_confidence is None
    assert report.calibration_quality is None
    assert report.total_in == 0
    assert cumulative.total_frames == 1
    assert cumulative.total_unique_tracks == 1
    assert cumulative.avg_fps == 24.0
