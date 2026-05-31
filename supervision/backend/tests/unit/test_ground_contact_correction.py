from __future__ import annotations

import pytest
from domain.speed.ground_contact import GroundContactCorrector


def test_ground_contact_correction_suppresses_bbox_bottom_jitter() -> None:
    corrector = GroundContactCorrector()
    y_values: list[float] = []

    for frame_index in range(10):
        y2 = 100.0 + (8.0 if frame_index % 2 == 0 else -8.0)
        point = corrector.correct(
            tracker_id=7,
            class_id=0,
            xyxy=[40.0 + frame_index * 2.0, 20.0, 60.0 + frame_index * 2.0, y2],
            timestamp_sec=frame_index / 25.0,
        )
        y_values.append(point.pixel[1])

    raw_span = 16.0
    corrected_span = max(y_values[2:]) - min(y_values[2:])
    assert corrected_span < raw_span * 0.45


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

    assert second.pixel[0] - first.pixel[0] == pytest.approx(20.0)
    assert second.confidence >= 0.75
