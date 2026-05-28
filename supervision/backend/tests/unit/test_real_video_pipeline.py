from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts import run_real_video_pipeline
from scripts.run_real_video_pipeline import apply_tuning_summary


def test_run_pipeline_writes_manifest_and_reports(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    def fake_prepare_assets(**_kwargs: object) -> None:
        return None

    def fake_validate_catalog(
        _path: Path,
        required_clips: list[str] | None = None,
    ) -> dict[str, object]:
        return {
            "video_calibration_count": 0,
            "pass_count": 0,
            "fail_count": 0,
            "industrial_readiness": "not_ready",
            "required_clips": required_clips or [],
            "missing_required_clips": required_clips or [],
            "readiness_issues": ["missing_required_video_calibration"],
            "rows": [],
            "preset_path": "preset.json",
        }

    def fake_run_analyze(_args: argparse.Namespace, output_dir: Path) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "summary.json").write_text(
            json.dumps({"summary": {}, "results": []}),
        )

    def fake_build_benchmark_summary(_payload: dict[str, object]) -> dict[str, object]:
        return {
            "total_successful_clips": 0,
            "avg_track_speed_confidence": None,
            "avg_speed_uncertainty_kmh": None,
            "mps_available": False,
            "mps_built": True,
            "quality_counts": {"pass": 0, "warn": 0, "fail": 0},
            "rows": [],
        }

    monkeypatch.setattr(run_real_video_pipeline, "prepare_assets", fake_prepare_assets)
    monkeypatch.setattr(run_real_video_pipeline, "validate_catalog", fake_validate_catalog)
    monkeypatch.setattr(run_real_video_pipeline, "_run_analyze", fake_run_analyze)
    monkeypatch.setattr(
        run_real_video_pipeline,
        "build_benchmark_summary",
        fake_build_benchmark_summary,
    )
    args = argparse.Namespace(
        input_dir="videos",
        output_dir=str(tmp_path / "pipeline"),
        calibration_presets="preset.json",
        clips=["clip.mp4"],
        limit=1,
        sample_per_profile=0,
        frame_index=1,
        max_frames=2,
        frame_stride=1,
        confidence=0.35,
        device="cpu",
        tuning_summary=None,
    )

    manifest = run_real_video_pipeline.run_pipeline(args)

    manifest_path = tmp_path / "pipeline" / "pipeline_manifest.json"
    assert manifest_path.exists()
    assert manifest["clips"] == ["clip.mp4"]
    assert manifest["manual_calibration_count"] == 0
    assert manifest["quality_counts"] == {"pass": 0, "warn": 0, "fail": 0}
    assert manifest["analysis_parameters"]["confidence"] == 0.35


def test_apply_tuning_summary_overrides_pipeline_parameters(tmp_path: Path) -> None:
    tuning_path = tmp_path / "tuning_summary.json"
    tuning_path.write_text(
        json.dumps(
            {
                "clip": "clip.mp4",
                "best_trial": {
                    "clip": "clip.mp4",
                    "confidence_threshold": 0.3,
                    "frame_stride": 12,
                    "max_frames": 18,
                    "device": "cpu",
                    "tuning_score": 0.82,
                },
            },
        ),
    )
    args = argparse.Namespace(
        clips=["clip.mp4"],
        confidence=0.35,
        frame_stride=10,
        max_frames=24,
        device="cpu",
        tuning_summary=str(tuning_path),
    )

    applied = apply_tuning_summary(args)

    assert applied is not None
    assert applied["applied"] is True
    assert args.confidence == 0.3
    assert args.frame_stride == 12
    assert args.max_frames == 18


def test_apply_tuning_summary_skips_unrequested_clip(tmp_path: Path) -> None:
    tuning_path = tmp_path / "tuning_summary.json"
    tuning_path.write_text(
        json.dumps(
            {
                "clip": "other.mp4",
                "best_trial": {
                    "clip": "other.mp4",
                    "confidence_threshold": 0.3,
                    "frame_stride": 12,
                    "max_frames": 18,
                },
            },
        ),
    )
    args = argparse.Namespace(
        clips=["clip.mp4"],
        confidence=0.35,
        frame_stride=10,
        max_frames=24,
        device="cpu",
        tuning_summary=str(tuning_path),
    )

    applied = apply_tuning_summary(args)

    assert applied is not None
    assert applied["applied"] is False
    assert args.confidence == 0.35
