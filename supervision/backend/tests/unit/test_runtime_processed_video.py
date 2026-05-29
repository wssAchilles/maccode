from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from application.services.runtime_state import PROCESSED_VIDEO_DIR, DemoRuntime
from scripts import analyze_real_videos
from scripts.generate_demo_report import generate_demo_report


def test_runtime_exposes_processed_mp4_url_for_real_video(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = DemoRuntime()
    processed_path = PROCESSED_VIDEO_DIR / "demo_processed.mp4"
    processed_path.parent.mkdir(parents=True, exist_ok=True)
    processed_path.write_bytes(b"mp4")

    def fake_analyze_video_source(_path: Path) -> dict[str, Any]:
        report = generate_demo_report()
        return {
            "clip": "demo.mp4",
            "device": "cpu",
            "calibration": {"source": "video_manual_preset"},
            "processed_video": {"path": str(processed_path), "filename": processed_path.name},
            "final_report": report,
            "frame_reports": [report],
        }

    monkeypatch.setattr(runtime, "_analyze_video_source", fake_analyze_video_source)

    task = runtime.start_task("file:///tmp/demo.mp4")
    payload = task.to_dict()

    assert payload["analysis_status"] == "real_video"
    assert payload["analysis_device"] == "cpu"
    assert payload["calibration_source"] == "video_manual_preset"
    assert payload["processed_video_url"].startswith(
        "http://127.0.0.1:8000/media/processed_videos/demo_processed.mp4?v="
    )


def test_runtime_real_video_analysis_uses_full_video_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = DemoRuntime()
    captured: dict[str, Any] = {}

    def fake_analyze_clip(**kwargs: Any) -> dict[str, Any]:
        captured.update(kwargs)
        report = generate_demo_report()
        processed_path = PROCESSED_VIDEO_DIR / "full_processed.mp4"
        return {
            "clip": "full.mp4",
            "calibration": {"source": "video_manual_preset"},
            "processed_video": {"path": str(processed_path), "filename": processed_path.name},
            "final_report": report,
            "frame_reports": [report],
        }

    monkeypatch.setattr(analyze_real_videos, "analyze_clip", fake_analyze_clip)

    runtime._analyze_video_source(Path("/tmp/full.mp4"))  # noqa: SLF001

    assert captured["frame_stride"] == 1
    assert captured["max_frames"] is None
    assert captured["processed_output_dir"] == PROCESSED_VIDEO_DIR


def test_runtime_applies_golden_clip_confidence_without_skipping_frames(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = DemoRuntime()
    captured: dict[str, Any] = {}

    def fake_analyze_clip(**kwargs: Any) -> dict[str, Any]:
        captured.update(kwargs)
        report = generate_demo_report()
        processed_path = PROCESSED_VIDEO_DIR / "golden_processed.mp4"
        return {
            "clip": "026_complex_signal_day_wide_0115s_30s.mp4",
            "calibration": {"source": "video_manual_preset"},
            "processed_video": {"path": str(processed_path), "filename": processed_path.name},
            "final_report": report,
            "frame_reports": [report],
        }

    monkeypatch.setattr(analyze_real_videos, "analyze_clip", fake_analyze_clip)

    runtime._analyze_video_source(  # noqa: SLF001
        Path("/tmp/026_complex_signal_day_wide_0115s_30s.mp4"),
    )

    assert captured["confidence"] == 0.45
    assert captured["frame_stride"] == 1
    assert captured["max_frames"] is None


def test_runtime_starts_playback_at_first_measured_report(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = DemoRuntime()
    processed_path = PROCESSED_VIDEO_DIR / "measured_processed.mp4"

    empty_report = generate_demo_report() | {
        "active_tracks": [],
        "regional_people_count": {"people_count": 0},
        "traffic_flow": {"space_mean_speed_kmh": None},
    }
    measured_report = generate_demo_report() | {
        "active_tracks": [
            {
                "tracker_id": 9,
                "class_id": 2,
                "class_name": "car",
                "confidence": 0.9,
                "xyxy": [0.0, 0.0, 10.0, 10.0],
                "first_seen_frame": 1,
                "last_seen_frame": 2,
                "speed_kmh": 35.0,
                "speed_uncertainty_kmh": 2.0,
                "speed_confidence": 0.85,
                "speed_confidence_interval_kmh": [33.0, 37.0],
                "position_rmse_m": 1.0,
                "ground_x_m": 5.0,
                "ground_y_m": 12.0,
                "velocity_x_mps": 8.0,
                "velocity_y_mps": 1.0,
                "heading_deg": 7.0,
                "acceleration_mps2": 0.1,
            },
        ],
    }

    def fake_analyze_video_source(_path: Path) -> dict[str, Any]:
        return {
            "clip": "measured.mp4",
            "device": "cpu",
            "calibration": {"source": "camera_manual_preset"},
            "processed_video": {"path": str(processed_path), "filename": processed_path.name},
            "final_report": measured_report,
            "frame_reports": [empty_report, measured_report],
        }

    monkeypatch.setattr(runtime, "_analyze_video_source", fake_analyze_video_source)

    runtime.start_task("file:///tmp/measured.mp4")

    assert runtime.get_realtime_report()["active_tracks"][0]["speed_kmh"] == 35.0


def test_runtime_preserves_real_video_profile_zone_stats() -> None:
    runtime = DemoRuntime()
    real_report = generate_demo_report() | {
        "zone_stats": [{"name": "profile_stop_line", "in_count": 3, "out_count": 1}],
        "total_in": 3,
        "total_out": 1,
        "calibration_diagnostics": {
            "calibration_source": "camera_manual_preset",
        },
    }

    updated = runtime._with_current_zones(real_report)  # noqa: SLF001

    assert updated["zone_stats"] == [
        {"name": "profile_stop_line", "in_count": 3, "out_count": 1}
    ]
    assert updated["total_in"] == 3
    assert updated["total_out"] == 1
