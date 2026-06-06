from __future__ import annotations

from domain.speed.ground_contact import GroundContactCorrector


def test_ground_contact_correction_suppresses_bbox_bottom_jitter() -> None:
    corrector = GroundContactCorrector()
    x_values: list[float] = []
    y_values: list[float] = []

    for frame_index in range(10):
        x_jitter = 5.0 if frame_index % 2 == 0 else -5.0
        y2 = 100.0 + (8.0 if frame_index % 2 == 0 else -8.0)
        point = corrector.correct(
            tracker_id=7,
            class_id=0,
            xyxy=[
                40.0 + frame_index * 2.0 + x_jitter,
                20.0,
                60.0 + frame_index * 2.0 + x_jitter,
                y2,
            ],
            timestamp_sec=frame_index / 25.0,
        )
        x_values.append(point.pixel[0] - frame_index * 2.0)
        y_values.append(point.pixel[1])

    raw_y_span = 16.0
    raw_x_span = 10.0
    corrected_span = max(y_values[2:]) - min(y_values[2:])
    corrected_x_span = max(x_values[2:]) - min(x_values[2:])
    assert corrected_span < raw_y_span * 0.45
    assert corrected_x_span < raw_x_span * 0.65


def test_ground_contact_correction_keeps_longitudinal_motion_responsive() -> None:
    corrector = GroundContactCorrector()

    first = corrector.correct(
        tracker_id=11,
        class_id=2,
        xyxy=[100.0, 120.0, 180.0, 180.0],
        timestamp_sec=0.0,
    )
    second = corrector.correct(
        tracker_id=11,
        class_id=2,
        xyxy=[120.0, 120.0, 200.0, 182.0],
        timestamp_sec=0.1,
    )

    assert second.pixel[0] - first.pixel[0] >= 14.0
    assert second.confidence >= 0.65


def test_vehicle_contact_reports_observation_sigma_when_bbox_size_drifts() -> None:
    corrector = GroundContactCorrector()
    first = corrector.correct(
        tracker_id=21,
        class_id=2,
        xyxy=[100.0, 120.0, 180.0, 180.0],
        timestamp_sec=0.0,
    )
    drifted = corrector.correct(
        tracker_id=21,
        class_id=2,
        xyxy=[104.0, 120.0, 220.0, 205.0],
        timestamp_sec=0.1,
    )

    assert first.observation_sigma_px > 0.0
    assert drifted.observation_sigma_px > first.observation_sigma_px
    assert drifted.measurement_source == "temporal_ground_contact_correction"
