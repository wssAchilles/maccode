from __future__ import annotations

import json
from pathlib import Path

from scripts.build_defense_packet import build_packet_summary, render_readme


def test_build_packet_summary_extracts_primary_demo(tmp_path: Path) -> None:
    pipeline_dir = tmp_path / "pipeline"
    tuning_dir = tmp_path / "tuning"
    readiness_dir = tmp_path / "readiness"
    analysis_dir = pipeline_dir / "analysis"
    calibration_dir = pipeline_dir / "calibration_validation"
    assets_dir = pipeline_dir / "calibration_assets"
    analysis_dir.mkdir(parents=True)
    calibration_dir.mkdir()
    assets_dir.mkdir()
    tuning_dir.mkdir()
    readiness_dir.mkdir()
    (pipeline_dir / "pipeline_manifest.json").write_text(
        json.dumps(
            {
                "analysis": str(analysis_dir),
                "calibration_validation": str(calibration_dir),
                "calibration_assets": str(assets_dir),
                "clips": ["clip.mp4"],
                "manual_calibration_count": 0,
            },
        ),
    )
    (analysis_dir / "benchmark_summary.json").write_text(
        json.dumps(
            {
                "quality_counts": {"pass": 0, "warn": 0, "fail": 1},
                "avg_physical_quantity_score": 0.86,
                "rows": [
                    {
                        "clip": "clip.mp4",
                        "quality_status": "fail",
                        "quality_issues": ["demo_calibration"],
                        "recommendations": ["add manual calibration"],
                        "avg_speed_confidence": 0.7,
                        "avg_speed_uncertainty_kmh": 17.0,
                        "physical_quantity_score": 0.86,
                    },
                ],
            },
        ),
    )
    (calibration_dir / "calibration_validation.json").write_text(
        json.dumps({"video_calibration_count": 0, "pass_count": 0, "fail_count": 0}),
    )
    (tuning_dir / "tuning_summary.json").write_text(
        json.dumps(
            {
                "clip": "clip.mp4",
                "trial_count": 4,
                "successful_trial_count": 4,
                "avg_tuning_score": 0.7,
                "best_trial": {
                    "confidence_threshold": 0.3,
                    "frame_stride": 12,
                    "max_frames": 18,
                    "quality_status": "warn",
                    "quality_issues": ["demo_calibration"],
                    "tuning_score": 0.82,
                    "avg_speed_confidence": 0.82,
                    "avg_speed_uncertainty_kmh": 3.56,
                    "physical_quantity_score": 1.0,
                    "effective_processing_fps": 22.0,
                },
            },
        ),
    )
    (readiness_dir / "demo_readiness.json").write_text(
        json.dumps(
            {
                "demo_readiness": "ready",
                "industrial_readiness": "not_ready",
                "demo_issues": [],
                "industrial_issues": ["missing_required_video_calibration"],
                "next_actions": ["add manual calibration"],
            },
        ),
    )

    summary = build_packet_summary(pipeline_dir, tuning_dir, readiness_dir)
    readme = render_readme(summary)

    assert summary["primary_demo"]["clip"] == "clip.mp4"
    assert summary["primary_demo"]["quality_status"] == "fail"
    assert summary["tuning"]["best_trial"]["frame_stride"] == 12
    assert summary["readiness"]["demo_readiness"] == "ready"
    assert "Readiness Gate" in readme
    assert "Industrial readiness: `not_ready`" in readme
    assert "Best Tuned Parameters" in readme
    assert "Tuning report" in readme
    assert "No per-video manual calibration preset" in readme
