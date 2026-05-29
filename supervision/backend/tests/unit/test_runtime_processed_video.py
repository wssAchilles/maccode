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
