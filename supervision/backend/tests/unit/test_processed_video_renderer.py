from __future__ import annotations

from domain.speed.pedestrian_quality import annotate_pedestrian_speed_reports
from infrastructure.cv.processed_video_renderer import ProcessedVideoRenderer


def test_renderer_ignores_reconstructed_track_without_pixel_box() -> None:
    track = {
        "tracker_id": 13,
        "class_id": 0,
        "class_name": "reconstructed",
        "confidence": 0.0,
        "ground_x_m": 12.0,
        "ground_y_m": 4.0,
        "speed_kmh": 5.0,
        "reconstructed": True,
    }

    assert ProcessedVideoRenderer._track_box(track) is None


def test_renderer_accepts_numeric_pixel_box() -> None:
    track = {
        "tracker_id": 9,
        "xyxy": ["1.2", 2, 10.6, 12.1],
    }

    assert ProcessedVideoRenderer._track_box(track) == (1, 2, 11, 12)


def test_renderer_hides_invalid_person_speed_instead_of_na_stable() -> None:
    track = {
        "tracker_id": 30,
        "class_id": 0,
        "class_name": "person",
        "speed_kmh": 15.5,
        "physics_valid": False,
        "quality_label": "geometry_invalid",
        "rejection_reason": "person_metric_plane_required",
    }

    label = ProcessedVideoRenderer._track_label(track, 30)

    assert "15.5 km/h" not in label
    assert label == "#30 person"
    assert "N/A" not in label
    assert "geometry_invalid" not in label


def test_pedestrian_annotation_hides_high_id_switch_risk_speed() -> None:
    reports = [
        {
            "active_tracks": [
                {
                    "tracker_id": 31,
                    "class_id": 0,
                    "class_name": "person",
                    "speed_kmh": 12.0,
                    "physics_valid": True,
                    "id_switch_risk": 0.82,
                    "xyxy": [1, 2, 10, 20],
                },
            ],
        },
    ]

    annotate_pedestrian_speed_reports(reports)
    track = reports[0]["active_tracks"][0]
    label = ProcessedVideoRenderer._track_label(track, 31)

    assert track["physics_valid"] is False
    assert track["speed_display_hidden"] is True
    assert track["pedestrian_speed_display_state"] == "id_switch_hidden"
    assert label == "#31 person"
    assert "12.0 km/h" not in label


def test_renderer_omits_speed_text_for_static_infrastructure() -> None:
    track = {
        "tracker_id": 3,
        "class_id": 9,
        "class_name": "traffic light",
        "speed_kmh": None,
        "physics_valid": False,
    }

    label = ProcessedVideoRenderer._track_label(track, 3)

    assert label == "#3 traffic light"
    assert "N/A" not in label


def test_renderer_hides_invalid_vehicle_speed_instead_of_na_stable() -> None:
    track = {
        "tracker_id": 63,
        "class_id": 2,
        "class_name": "car",
        "speed_kmh": None,
        "physics_valid": False,
        "quality_label": "stable",
        "vehicle_speed_display_state": "rejected_hidden",
        "speed_display_hidden": True,
    }

    label = ProcessedVideoRenderer._track_label(track, 63)

    assert label == "#63 car"
    assert "N/A" not in label
    assert "stable" not in label


def test_renderer_prints_frozen_vehicle_speed_as_metric_speed() -> None:
    track = {
        "tracker_id": 64,
        "class_id": 2,
        "class_name": "car",
        "speed_kmh": 42.25,
        "physics_valid": True,
        "speed_source": "frozen_last_valid",
        "vehicle_speed_display_state": "frozen_last_valid",
    }

    label = ProcessedVideoRenderer._track_label(track, 64)

    assert label == "#64 car 42.2 km/h"
