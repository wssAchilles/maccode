from __future__ import annotations

from scripts.summarize_real_video_benchmark import (
    build_benchmark_summary,
    grade_row,
    render_markdown,
)


def test_build_benchmark_summary_extracts_physical_semantics() -> None:
    payload = {
        "summary": {"mps_available": False, "mps_built": True},
        "results": [
            {
                "status": "ok",
                "clip": "clip.mp4",
                "scene_profile": {"name": "wide"},
                "calibration": {
                    "source": "scene_profile_preset",
                    "quality": "excellent",
                    "position_rmse_floor_m": 1.5,
                    "scale_uncertainty_pct": 8.0,
                },
                "sensitivity": {"space_mean_speed_band_kmh": [10.0, 12.0]},
                "effective_processing_fps": 14.5,
                "final_report": {
                    "active_tracks": [
                        {
                            "speed_kmh": 11.0,
                            "speed_confidence": 0.8,
                            "speed_uncertainty_kmh": 1.2,
                        },
                        {"speed_kmh": None},
                    ],
                    "regional_people_count": {"people_count": 3},
                    "infrastructure_semantics": {"traffic_light_count": 2},
                    "traffic_flow": {
                        "space_mean_speed_kmh": 11.0,
                        "congestion_level": "stable_flow",
                    },
                    "safety_metrics": {"risk_level": "nominal"},
                },
            },
        ],
    }

    summary = build_benchmark_summary(payload)
    markdown = render_markdown(summary)

    assert summary["total_successful_clips"] == 1
    assert summary["rows"][0]["people_count"] == 3
    assert summary["rows"][0]["traffic_light_count"] == 2
    assert summary["rows"][0]["avg_speed_confidence"] == 0.8
    assert summary["rows"][0]["quality_status"] == "warn"
    assert summary["quality_counts"] == {"pass": 0, "warn": 1, "fail": 0}
    assert "clip.mp4" in markdown


def test_quality_gate_fails_low_confidence_high_uncertainty_rows() -> None:
    grade = grade_row(
        {
            "calibration_source": "scene_profile_preset",
            "speed_tracks": 2,
            "avg_speed_confidence": 0.2,
            "avg_speed_uncertainty_kmh": 30.0,
            "effective_processing_fps": 3.0,
        },
    )

    assert grade["quality_status"] == "fail"
    assert "low_speed_confidence" in grade["quality_issues"]
    assert "high_speed_uncertainty" in grade["quality_issues"]
    assert "slow_processing" in grade["quality_issues"]


def test_quality_gate_passes_manual_calibrated_stable_rows() -> None:
    grade = grade_row(
        {
            "calibration_source": "video_manual_preset",
            "speed_tracks": 3,
            "avg_speed_confidence": 0.8,
            "avg_speed_uncertainty_kmh": 5.0,
            "effective_processing_fps": 12.0,
        },
    )

    assert grade["quality_status"] == "pass"
    assert grade["quality_issues"] == []
