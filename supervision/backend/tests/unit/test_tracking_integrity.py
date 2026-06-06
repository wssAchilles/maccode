from __future__ import annotations

from domain.speed.models import SpeedRecord
from domain.tracking.integrity import TrackingIntegrityMonitor
from domain.tracking.models import Track


def _track(tracker_id: int, xyxy: list[float], class_id: int = 2) -> Track:
    return Track(
        tracker_id=tracker_id,
        class_id=class_id,
        class_name="car",
        confidence=0.9,
        xyxy=xyxy,
        first_seen_frame=1,
        last_seen_frame=1,
    )


def _record(timestamp_sec: float = 1.0, world_x: float = 0.0) -> SpeedRecord:
    return SpeedRecord(
        tracker_id=1,
        speed_kmh=36.0,
        timestamp_sec=timestamp_sec,
        world_x=world_x,
        world_y=0.0,
        velocity_x_mps=10.0,
        velocity_y_mps=0.0,
        physics_valid=True,
    )


def test_bev_position_jump_triggers_id_switch_freeze() -> None:
    monitor = TrackingIntegrityMonitor(freeze_frames=3)
    active_ids = {1}
    monitor.assess(
        _track(1, [0, 0, 20, 20]),
        world_position=(0.0, 0.0),
        timestamp_sec=1.0,
        previous_record=None,
        active_track_ids=active_ids,
    )

    result = monitor.assess(
        _track(1, [200, 0, 220, 20]),
        world_position=(80.0, 0.0),
        timestamp_sec=2.0,
        previous_record=_record(1.0),
        active_track_ids=active_ids,
    )

    assert result.state == "suspected_id_switch"
    assert result.speed_frozen is True
    assert result.id_switch_risk >= 0.75


def test_freeze_recovers_after_consistent_observations() -> None:
    monitor = TrackingIntegrityMonitor(freeze_frames=1)
    active_ids = {1}
    monitor.assess(
        _track(1, [0, 0, 20, 20]),
        world_position=(0.0, 0.0),
        timestamp_sec=1.0,
        previous_record=None,
        active_track_ids=active_ids,
    )
    monitor.assess(
        _track(1, [200, 0, 220, 20]),
        world_position=(80.0, 0.0),
        timestamp_sec=2.0,
        previous_record=_record(1.0),
        active_track_ids=active_ids,
    )

    result = monitor.assess(
        _track(1, [202, 0, 222, 20]),
        world_position=(90.0, 0.0),
        timestamp_sec=3.0,
        previous_record=_record(2.0, world_x=80.0),
        active_track_ids=active_ids,
    )

    assert result.state in {"recovered", "normal"}
