from __future__ import annotations

import json
from pathlib import Path

from scripts.build_math_model_card import build_model_card, render_markdown


def test_build_model_card_extracts_models_and_metrics(tmp_path: Path) -> None:
    analysis_path = tmp_path / "analysis.json"
    readiness_path = tmp_path / "readiness.json"
    analysis_path.write_text(
        json.dumps(
            {
                "clip": "clip.mp4",
                "calibration": {
                    "source": "scene_profile_preset",
                    "quality": "excellent",
                    "rmse": 0.2,
                    "inlier_count": 6,
                    "position_rmse_floor_m": 1.5,
                    "scale_uncertainty_pct": 8.0,
                },
                "sensitivity": {
                    "scale_uncertainty_pct": 8.0,
                    "speed_band_kmh": [9.0, 12.0],
                    "space_mean_speed_band_kmh": [10.0, 11.0],
                    "interpretation": "linear scale effect",
                },
                "final_report": {
                    "active_tracks": [
                        {
                            "tracker_id": 1,
                            "class_name": "car",
                            "speed_kmh": 10.0,
                            "speed_confidence": 0.9,
                            "speed_uncertainty_kmh": 1.2,
                            "speed_confidence_interval_kmh": [8.8, 11.2],
                            "ground_x_m": 1.0,
                            "ground_y_m": 2.0,
                            "heading_deg": 90.0,
                            "acceleration_mps2": 0.1,
                        },
                    ],
                    "traffic_flow": {
                        "flow_q_veh_per_hour": 600.0,
                        "density_k_veh_per_km": 20.0,
                        "space_mean_speed_kmh": 30.0,
                        "congestion_level": "stable_flow",
                        "greenshields_speed_kmh": 45.0,
                    },
                    "safety_metrics": {
                        "vehicle_pair_count": 1,
                        "min_time_headway_sec": 2.0,
                        "min_time_to_collision_sec": 4.0,
                        "risk_level": "nominal",
                    },
                },
            },
        ),
    )
    readiness_path.write_text(
        json.dumps({"demo_readiness": "ready", "industrial_readiness": "not_ready"}),
    )

    card = build_model_card(analysis_path, readiness_path)
    markdown = render_markdown(card)

    assert card["clip"] == "clip.mp4"
    assert card["geometry_model"]["calibration_source"] == "scene_profile_preset"
    assert card["kinematics_model"]["avg_speed_confidence"] == 0.9
    assert card["traffic_flow_model"]["flow_q_veh_per_hour"] == 600.0
    assert "joint_speed_uncertainty_posterior_v1" in card["model_chain"]
    assert "nis_consistency_diagnostics_v1" in card["model_chain"]
    assert "synthetic_speed_parameter_sweep_v1" in card["model_chain"]
    assert "Math Model Card" in markdown
    assert "Absolute speed and Homography Grid claims remain suppressed" in markdown
