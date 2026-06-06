from __future__ import annotations

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
