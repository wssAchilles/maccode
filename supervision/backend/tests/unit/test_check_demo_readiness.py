from __future__ import annotations

import json
from pathlib import Path

from scripts.check_demo_readiness import build_readiness_report, render_markdown


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload))


def test_readiness_gate_allows_demo_but_blocks_industrial_without_manual_calibration(
    tmp_path: Path,
) -> None:
    pipeline_dir = tmp_path / "pipeline"
    tuning_dir = tmp_path / "tuning"
    analysis_dir = pipeline_dir / "analysis"
    validation_dir = pipeline_dir / "calibration_validation"
    _write_json(
        pipeline_dir / "pipeline_manifest.json",
        {
            "analysis": str(analysis_dir),
            "calibration_validation": str(validation_dir),
            "tuning_application": {"applied": True},
        },
    )
    _write_json(
        analysis_dir / "benchmark_summary.json",
        {
            "quality_counts": {"pass": 0, "warn": 1, "fail": 0},
            "rows": [
                {
                    "clip": "clip.mp4",
                    "quality_status": "warn",
                    "quality_issues": ["demo_calibration"],
                    "avg_speed_confidence": 0.82,
                    "avg_speed_uncertainty_kmh": 3.5,
                    "physical_quantity_score": 1.0,
                    "effective_processing_fps": 12.0,
                    "calibration_source": "scene_profile_preset",
                },
            ],
        },
    )
    _write_json(
        validation_dir / "calibration_validation.json",
        {"industrial_readiness": "not_ready", "readiness_issues": ["missing_manual"]},
    )
    _write_json(tuning_dir / "tuning_summary.json", {"best_trial": {"tuning_score": 0.82}})

    report = build_readiness_report(pipeline_dir, tuning_dir)
    markdown = render_markdown(report)

    assert report["demo_readiness"] == "ready"
    assert report["industrial_readiness"] == "not_ready"
    assert "calibration_source_not_video_manual_preset" in report["industrial_issues"]
    assert "Demo readiness" in markdown


def test_readiness_gate_fails_demo_when_tuning_not_applied(tmp_path: Path) -> None:
    pipeline_dir = tmp_path / "pipeline"
    tuning_dir = tmp_path / "tuning"
    analysis_dir = pipeline_dir / "analysis"
    validation_dir = pipeline_dir / "calibration_validation"
    _write_json(
        pipeline_dir / "pipeline_manifest.json",
        {
            "analysis": str(analysis_dir),
            "calibration_validation": str(validation_dir),
            "tuning_application": {"applied": False},
        },
    )
    _write_json(
        analysis_dir / "benchmark_summary.json",
        {
            "quality_counts": {"pass": 0, "warn": 0, "fail": 1},
            "rows": [
                {
                    "clip": "clip.mp4",
                    "quality_status": "fail",
                    "avg_speed_confidence": 0.6,
                    "avg_speed_uncertainty_kmh": 20.0,
                    "physical_quantity_score": 0.8,
                    "effective_processing_fps": 3.0,
                    "calibration_source": "scene_profile_preset",
                },
            ],
        },
    )
    _write_json(
        validation_dir / "calibration_validation.json",
        {"industrial_readiness": "not_ready", "readiness_issues": []},
    )
    _write_json(tuning_dir / "tuning_summary.json", {"best_trial": {"tuning_score": 0.5}})

    report = build_readiness_report(pipeline_dir, tuning_dir)

    assert report["demo_readiness"] == "not_ready"
    assert "tuning_not_applied_to_pipeline" in report["demo_issues"]
    assert "demo_quality_below_warn" in report["demo_issues"]
