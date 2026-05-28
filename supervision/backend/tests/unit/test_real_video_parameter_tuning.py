from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from scripts import tune_real_video_parameters
from scripts.tune_real_video_parameters import (
    parse_float_grid,
    parse_int_grid,
    render_markdown,
    run_tuning,
    tuning_score,
)


def test_parse_grid_casts_values() -> None:
    assert parse_float_grid("0.25,0.35") == [0.25, 0.35]
    assert parse_int_grid("8,10") == [8, 10]


def test_tuning_score_rewards_confidence_uncertainty_and_physics() -> None:
    weak = {
        "quality_status": "fail",
        "avg_speed_confidence": 0.3,
        "avg_speed_uncertainty_kmh": 24.0,
        "physical_quantity_score": 0.5,
        "effective_processing_fps": 4.0,
        "speed_tracks": 1,
    }
    strong = {
        "quality_status": "pass",
        "avg_speed_confidence": 0.9,
        "avg_speed_uncertainty_kmh": 4.0,
        "physical_quantity_score": 1.0,
        "effective_processing_fps": 14.0,
        "speed_tracks": 5,
    }

    assert tuning_score(strong) > tuning_score(weak)


def test_run_tuning_ranks_trials(tmp_path: Path, monkeypatch: Any) -> None:
    def fake_analyze_clip(**kwargs: Any) -> dict[str, object]:
        confidence = float(kwargs["confidence"])
        speed_confidence = 0.65 if confidence < 0.4 else 0.85
        uncertainty = 18.0 if confidence < 0.4 else 6.0
        return {
            "clip": "clip.mp4",
            "status": "ok",
            "scene_profile": {"name": "road"},
            "calibration": {
                "source": "video_manual_preset",
                "quality": "excellent",
                "position_rmse_floor_m": 0.4,
                "scale_uncertainty_pct": 2.5,
            },
            "sensitivity": {"space_mean_speed_band_kmh": [38.0, 42.0]},
            "effective_processing_fps": 10.0,
            "final_report": {
                "active_tracks": [
                    {
                        "speed_kmh": 40.0,
                        "speed_confidence": speed_confidence,
                        "speed_uncertainty_kmh": uncertainty,
                        "speed_confidence_interval_kmh": [37.0, 43.0],
                        "ground_x_m": 20.0,
                        "ground_y_m": 5.0,
                        "velocity_x_mps": 11.0,
                        "velocity_y_mps": 0.0,
                        "heading_deg": 0.0,
                        "acceleration_mps2": 0.0,
                    },
                ],
                "regional_people_count": {"people_count": 0},
                "infrastructure_semantics": {
                    "traffic_light_count": 1,
                    "static_context": [],
                },
                "traffic_flow": {
                    "flow_q_veh_per_hour": 900.0,
                    "density_k_veh_per_km": 22.5,
                    "space_mean_speed_kmh": 40.0,
                    "congestion_level": "stable_flow",
                },
                "safety_metrics": {
                    "risk_level": "nominal",
                    "min_time_to_collision_sec": None,
                    "min_time_headway_sec": 2.4,
                },
            },
        }

    monkeypatch.setattr(tune_real_video_parameters, "analyze_clip", fake_analyze_clip)
    args = argparse.Namespace(
        input_dir=str(tmp_path),
        clip="clip.mp4",
        output_dir=str(tmp_path),
        calibration_presets=str(tmp_path / "missing.json"),
        confidences="0.25,0.45",
        frame_strides="10",
        max_frames_values="12",
        model="model.pt",
        device="cpu",
    )

    summary = run_tuning(args)
    markdown = render_markdown(summary)

    assert summary["trial_count"] == 2
    assert summary["best_trial"]["confidence_threshold"] == 0.45
    assert summary["best_trial"]["quality_status"] == "pass"
    assert "## Trial Matrix" in markdown
