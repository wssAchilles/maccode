from __future__ import annotations

from domain.tracking.tracklet_reassociation import TrackletReAssociationService


def _report(frame_index: int, tracker_id: int, x: float) -> dict[str, object]:
    return {
        "frame_index": frame_index,
        "timestamp_sec": float(frame_index),
        "active_tracks": [
            {
                "tracker_id": tracker_id,
                "class_id": 2,
                "ground_x_m": x,
                "ground_y_m": 0.0,
                "velocity_x_mps": 10.0,
                "velocity_y_mps": 0.0,
                "speed_kmh": 36.0,
            }
        ],
    }


def test_tracklet_reassociation_links_short_gap_with_consistent_bev_motion() -> None:
    reports = [
        _report(0, 1, 0.0),
        _report(1, 1, 10.0),
        {"frame_index": 2, "timestamp_sec": 2.0, "active_tracks": []},
        _report(3, 9, 30.0),
        _report(4, 9, 40.0),
    ]

    updated, summary = TrackletReAssociationService().relink_reports(reports)
    relinked = updated[3]["active_tracks"][0]

    assert summary.relinked_count == 1
    assert relinked["tracklet_relinked"] is True
    assert relinked["tracklet_parent_id"] == 1


def test_tracklet_reassociation_rejects_class_conflict() -> None:
    reports = [
        _report(0, 1, 0.0),
        _report(1, 1, 10.0),
        {
            "frame_index": 3,
            "timestamp_sec": 3.0,
            "active_tracks": [
                {
                    "tracker_id": 9,
                    "class_id": 0,
                    "ground_x_m": 30.0,
                    "ground_y_m": 0.0,
                    "velocity_x_mps": 10.0,
                    "velocity_y_mps": 0.0,
                    "speed_kmh": 36.0,
                }
            ],
        },
    ]

    updated, summary = TrackletReAssociationService().relink_reports(reports)

    assert summary.relinked_count == 0
    assert "tracklet_relinked" not in updated[-1]["active_tracks"][0]
