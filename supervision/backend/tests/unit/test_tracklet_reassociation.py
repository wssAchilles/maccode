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
                "heading_deg": 0.0,
                "plane_id": "lane_1",
                "id_switch_risk": 0.0,
            }
        ],
    }


def _track(
    tracker_id: int,
    class_id: int,
    x: float,
    y: float,
    vx: float,
    vy: float,
    *,
    id_switch_risk: float = 0.0,
) -> dict[str, object]:
    return {
        "tracker_id": tracker_id,
        "class_id": class_id,
        "ground_x_m": x,
        "ground_y_m": y,
        "velocity_x_mps": vx,
        "velocity_y_mps": vy,
        "speed_kmh": 36.0,
        "heading_deg": 0.0,
        "plane_id": "lane_1",
        "id_switch_risk": id_switch_risk,
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
    assert relinked["recovery_score"] >= 0.62
    assert relinked["tracklet_relink_reason"] == "bev_kinematic_reconnect"
    assert relinked["speed_source"] == "tracklet_reassociated_bev_kinematic"
    assert relinked["speed_uncertainty_kmh"] >= 3.0
    assert relinked["id_switch_risk"] < 0.7
    assert summary.to_dict()["model_reference"] == (
        "ocsort_strongsort_geometry_tracklet_reassociation_v1"
    )
    assert "OC-SORT observation-centric short-gap repair" in summary.to_dict()[
        "paper_alignment"
    ]


def test_tracklet_reassociation_uses_frame_index_for_sparse_gap_gate() -> None:
    reports = [
        {
            **_report(1, 1, 0.0),
            "timestamp_sec": None,
        },
        {
            **_report(2, 1, 1.0),
            "timestamp_sec": None,
        },
        {
            **_report(100, 9, 4.2),
            "timestamp_sec": None,
        },
        {
            **_report(101, 9, 5.2),
            "timestamp_sec": None,
        },
    ]

    updated, summary = TrackletReAssociationService().relink_reports(reports)

    assert summary.relinked_count == 0
    assert "tracklet_relinked" not in updated[2]["active_tracks"][0]


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


def test_tracklet_reassociation_enforces_one_child_per_parent() -> None:
    reports = [
        _report(0, 1, 0.0),
        _report(1, 1, 10.0),
        {
            "frame_index": 3,
            "timestamp_sec": 3.0,
            "active_tracks": [
                {
                    **_report(3, 9, 30.0)["active_tracks"][0],
                    "tracker_id": 9,
                },
                {
                    **_report(3, 10, 30.2)["active_tracks"][0],
                    "tracker_id": 10,
                },
            ],
        },
        {
            "frame_index": 4,
            "timestamp_sec": 4.0,
            "active_tracks": [
                {
                    "tracker_id": 9,
                    "class_id": 2,
                    "ground_x_m": 40.0,
                    "ground_y_m": 0.0,
                    "velocity_x_mps": 10.0,
                    "velocity_y_mps": 0.0,
                    "speed_kmh": 120.0,
                },
            ],
        },
        {
            "frame_index": 4,
            "timestamp_sec": 4.0,
            "active_tracks": [
                {
                    **_report(4, 9, 40.0)["active_tracks"][0],
                    "tracker_id": 9,
                },
                {
                    **_report(4, 10, 40.2)["active_tracks"][0],
                    "tracker_id": 10,
                },
            ],
        },
    ]

    updated, summary = TrackletReAssociationService().relink_reports(reports)
    relinked_children = [
        int(track["tracker_id"])
        for report in updated
        for track in report.get("active_tracks", [])
        if isinstance(track, dict) and track.get("tracklet_relinked")
    ]

    assert summary.relinked_count == 1
    assert len(set(relinked_children)) == 1


def test_tracklet_reassociation_rejects_speed_jump() -> None:
    reports = [
        _report(0, 1, 0.0),
        _report(1, 1, 10.0),
        {
            "frame_index": 3,
            "timestamp_sec": 3.0,
            "active_tracks": [
                {
                    "tracker_id": 9,
                    "class_id": 2,
                    "ground_x_m": 30.0,
                    "ground_y_m": 0.0,
                    "velocity_x_mps": 10.0,
                    "velocity_y_mps": 0.0,
                    "speed_kmh": 120.0,
                },
            ],
        },
        {
            "frame_index": 4,
            "timestamp_sec": 4.0,
            "active_tracks": [
                {
                    "tracker_id": 9,
                    "class_id": 2,
                    "ground_x_m": 40.0,
                    "ground_y_m": 0.0,
                    "velocity_x_mps": 10.0,
                    "velocity_y_mps": 0.0,
                    "speed_kmh": 120.0,
                },
            ],
        },
    ]

    updated, summary = TrackletReAssociationService().relink_reports(reports)

    assert summary.relinked_count == 0
    assert "tracklet_relinked" not in updated[-1]["active_tracks"][0]
    assert summary.to_dict()["rejected_reason_counts"]["speed_jump_gate"] >= 1


def test_tracklet_reassociation_rejects_high_id_switch_risk() -> None:
    reports = [
        _report(0, 1, 0.0),
        _report(1, 1, 10.0),
        {
            "frame_index": 3,
            "timestamp_sec": 3.0,
            "active_tracks": [
                {
                    "tracker_id": 9,
                    "class_id": 2,
                    "ground_x_m": 30.0,
                    "ground_y_m": 0.0,
                    "velocity_x_mps": 10.0,
                    "velocity_y_mps": 0.0,
                    "speed_kmh": 36.0,
                    "id_switch_risk": 0.9,
                },
            ],
        },
        {
            "frame_index": 4,
            "timestamp_sec": 4.0,
            "active_tracks": [
                {
                    "tracker_id": 9,
                    "class_id": 2,
                    "ground_x_m": 40.0,
                    "ground_y_m": 0.0,
                    "velocity_x_mps": 10.0,
                    "velocity_y_mps": 0.0,
                    "speed_kmh": 36.0,
                    "id_switch_risk": 0.9,
                },
            ],
        },
    ]

    updated, summary = TrackletReAssociationService().relink_reports(reports)

    assert summary.relinked_count == 0
    assert "tracklet_relinked" not in updated[-1]["active_tracks"][0]
    assert summary.to_dict()["rejected_reason_counts"]["id_switch_risk_gate"] >= 1


def test_tracklet_reassociation_rejects_mid_track_id_switch_risk() -> None:
    reports = [
        {
            "frame_index": 0,
            "timestamp_sec": 0.0,
            "active_tracks": [
                _track(1, 2, 0.0, 0.0, 10.0, 0.0, id_switch_risk=0.0),
            ],
        },
        {
            "frame_index": 1,
            "timestamp_sec": 1 / 30,
            "active_tracks": [
                _track(1, 2, 0.3, 0.0, 10.0, 0.0, id_switch_risk=0.9),
            ],
        },
        {
            "frame_index": 2,
            "timestamp_sec": 2 / 30,
            "active_tracks": [
                _track(1, 2, 0.6, 0.0, 10.0, 0.0, id_switch_risk=0.0),
            ],
        },
        {
            "frame_index": 4,
            "timestamp_sec": 4 / 30,
            "active_tracks": [
                _track(2, 2, 1.2, 0.0, 10.0, 0.0, id_switch_risk=0.0),
            ],
        },
        {
            "frame_index": 5,
            "timestamp_sec": 5 / 30,
            "active_tracks": [
                _track(2, 2, 1.5, 0.0, 10.0, 0.0, id_switch_risk=0.0),
            ],
        },
    ]

    updated, summary = TrackletReAssociationService().relink_reports(reports)

    assert summary.relinked_count == 0
    assert "tracklet_relinked" not in updated[-1]["active_tracks"][0]
    assert summary.to_dict()["rejected_reason_counts"]["id_switch_risk_gate"] >= 1
