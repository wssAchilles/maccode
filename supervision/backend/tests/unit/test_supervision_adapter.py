from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace
from typing import Any, cast

import numpy as np
import pytest
from domain.detection.models import Detection, Detections
from infrastructure.cv.supervision_adapter import SupervisionRuntimeAdapter


class FakeSvDetections:
    def __init__(self, xyxy: np.ndarray, confidence: np.ndarray, class_id: np.ndarray) -> None:
        self.xyxy = xyxy
        self.confidence = confidence
        self.class_id = class_id
        self.tracker_id = np.array([], dtype=int)


class FakeByteTrack:
    def update_with_detections(self, detections: FakeSvDetections) -> FakeSvDetections:
        detections.tracker_id = np.arange(1, len(detections.xyxy) + 1)
        return detections


class FakeLineZone:
    created_count = 0

    def __init__(self, start: object, end: object) -> None:
        type(self).created_count += 1
        self.start = start
        self.end = end
        self.in_count = 1
        self.out_count = 0

    def trigger(self, detections: FakeSvDetections) -> None:
        self.in_count = len(detections.xyxy)


def install_fake_supervision(monkeypatch: pytest.MonkeyPatch) -> None:
    FakeLineZone.created_count = 0
    fake = ModuleType("supervision")
    fake_any = cast(Any, fake)
    fake_any.Detections = FakeSvDetections
    fake_any.ByteTrack = FakeByteTrack
    fake_any.LineZone = FakeLineZone
    fake_any.Point = lambda x, y: SimpleNamespace(x=x, y=y)
    monkeypatch.setitem(sys.modules, "supervision", fake)


def test_supervision_adapter_converts_domain_detections_to_tracks_and_zone_counts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_supervision(monkeypatch)
    detections = Detections(
        items=[Detection([0, 0, 10, 10], 0.9, 2, "car")],
        frame_index=1,
        timestamp_sec=0.0,
    )

    result = SupervisionRuntimeAdapter().track_and_count(
        detections,
        line_start=(0.0, 5.0),
        line_end=(20.0, 5.0),
    )

    assert result.tracks[0].tracker_id == 1
    assert result.tracks[0].class_name == "car"
    assert result.zone_stats.in_count == 1


def test_supervision_adapter_reuses_line_zone_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_supervision(monkeypatch)
    adapter = SupervisionRuntimeAdapter()
    detections = Detections(
        items=[Detection([0, 0, 10, 10], 0.9, 2, "car")],
        frame_index=1,
        timestamp_sec=0.0,
    )

    adapter.track_and_count(detections, line_start=(0.0, 5.0), line_end=(20.0, 5.0))
    adapter.track_and_count(detections, line_start=(0.0, 5.0), line_end=(20.0, 5.0))

    assert FakeLineZone.created_count == 1


def test_supervision_adapter_uses_tracked_class_id_for_class_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class ReorderingByteTrack:
        def update_with_detections(self, detections: FakeSvDetections) -> FakeSvDetections:
            detections.tracker_id = np.array([1], dtype=int)
            detections.class_id = np.array([9], dtype=int)
            detections.confidence = np.array([0.7], dtype=float)
            detections.xyxy = np.array([[20.0, 20.0, 30.0, 30.0]], dtype=float)
            return detections

    install_fake_supervision(monkeypatch)
    fake_module = cast(Any, sys.modules["supervision"])
    fake_module.ByteTrack = ReorderingByteTrack
    detections = Detections(
        items=[
            Detection([0, 0, 10, 10], 0.9, 2, "car"),
            Detection([20, 20, 30, 30], 0.7, 9, "traffic light"),
        ],
        frame_index=1,
        timestamp_sec=0.0,
    )

    result = SupervisionRuntimeAdapter().track_and_count(
        detections,
        line_start=(0.0, 5.0),
        line_end=(20.0, 5.0),
    )

    assert result.tracks[0].class_id == 9
    assert result.tracks[0].class_name == "traffic light"
