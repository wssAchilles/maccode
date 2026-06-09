from __future__ import annotations

from typing import Any

from scripts.summarize_real_video_benchmark import (
    build_benchmark_summary,
    build_physical_quantity_coverage,
    grade_row,
    render_markdown,
)


def test_physical_quantity_coverage_audits_micro_macro_and_environment() -> None:
    report: dict[str, Any] = {
        "active_tracks": [
            {
                "speed_kmh": 42.0,
                "speed_uncertainty_kmh": 2.5,
                "speed_confidence_interval_kmh": [39.5, 44.5],
                "ground_x_m": 12.0,
                "ground_y_m": 3.0,
                "velocity_x_mps": 10.0,
                "velocity_y_mps": 0.5,
                "heading_deg": 2.8,
                "acceleration_mps2": 0.2,
            },
        ],
        "traffic_flow": {
            "flow_q_veh_per_hour": 720.0,
            "density_k_veh_per_km": 18.0,
            "space_mean_speed_kmh": 40.0,
            "congestion_level": "stable_flow",
        },
        "regional_people_count": {"people_count": 3},
        "infrastructure_semantics": {
            "traffic_light_count": 1,
            "static_context": [{"class_name": "traffic light"}],
        },
        "safety_metrics": {
            "risk_level": "nominal",
            "min_time_to_collision_sec": None,
            "min_time_headway_sec": 2.4,
        },
    }

    coverage = build_physical_quantity_coverage(report, report["active_tracks"])

    assert coverage["micro_kinematics"]["has_instantaneous_speed"] is True
    assert coverage["micro_kinematics"]["has_ground_coordinates"] is True
    assert coverage["micro_kinematics"]["has_speed_confidence_interval"] is True
    assert coverage["macro_statistics"]["has_traffic_flow"] is True
    assert coverage["environment_semantics"]["has_infrastructure_state"] is True
    assert coverage["environment_semantics"]["has_safety_metrics"] is True


def test_benchmark_summary_renders_physical_quantity_matrix() -> None:
    payload = {
        "summary": {
            "mps_available": False,
            "mps_built": True,
            "vehicle_speed_aggregate": {
                "vehicle_track_samples": 100,
                "displayable_vehicle_track_samples": 99,
                "vehicle_display_coverage": 0.99,
                "passes_dense_city_acceptance": False,
                "na_by_reason": {"warming_up_hidden": 1},
                "vehicle_3d_scale_sanity_available_count": 1,
                "vehicle_3d_calibration_region_quality_counts": {"review": 1},
                "vehicle_3d_review_clip_count": 1,
                "vehicle_3d_homography_uncertainty_multiplier_p95": 2.5,
                "clip_rows": [
                    {
                        "clip": "clip.mp4",
                        "coverage_used_for_acceptance": 0.99,
                        "passes_vehicle_speed_acceptance": False,
                        "displayed_low_confidence_ratio": 0.0,
                        "displayed_high_uncertainty_ratio": 0.0,
                        "hard_rejected_display_count": 0,
                        "displayed_id_switch_risk_count": 0,
                        "max_consecutive_frozen_frames": 0,
                        "vehicle_3d_calibration_region_quality": "review",
                        "max_speed_by_class": {"car": 40.0},
                    },
                ],
            },
        },
        "results": [
            {
                "status": "ok",
                "clip": "clip.mp4",
                "scene_profile": {"name": "road"},
                "calibration": {
                    "source": "video_manual_preset",
                    "quality": "excellent",
                    "position_rmse_floor_m": 0.4,
                    "scale_uncertainty_pct": 2.5,
                },
                "sensitivity": {"space_mean_speed_band_kmh": [38.0, 42.0]},
                "effective_processing_fps": 12.0,
                "final_report": {
                    "active_tracks": [
                        {
                            "speed_kmh": 40.0,
                            "speed_confidence": 0.92,
                            "speed_uncertainty_kmh": 3.0,
                            "speed_confidence_interval_kmh": [37.0, 43.0],
                            "ground_x_m": 20.0,
                            "ground_y_m": 5.0,
                            "velocity_x_mps": 11.0,
                            "velocity_y_mps": 0.0,
                            "heading_deg": 0.0,
                            "acceleration_mps2": 0.0,
                            "scale_confidence_label": "weak_scale",
                        },
                    ],
                    "calibration_diagnostics": {"weak_scale_mode": True},
                    "integrity_diagnostics": {
                        "contact_outlier_ratio": 0.25,
                        "optical_flow_low_inlier_ratio": 0.5,
                    },
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
            },
        ],
    }

    summary = build_benchmark_summary(payload)
    markdown = render_markdown(summary)

    assert summary["quality_counts"] == {"pass": 1, "warn": 0, "fail": 0}
    assert summary["avg_physical_quantity_score"] == 1.0
    assert summary["vehicle_speed_aggregate"]["vehicle_track_samples"] == 100
    assert summary["rows"][0]["physical_quantity_score"] == 1.0
    assert summary["rows"][0]["contact_outlier_ratio"] == 0.25
    assert summary["rows"][0]["optical_flow_low_inlier_ratio"] == 0.5
    assert summary["rows"][0]["weak_scale_track_count"] == 1
    assert summary["rows"][0]["weak_scale_mode"] is True
    assert "## Physical Quantity Coverage" in markdown
    assert "## Vehicle Speed Aggregate" in markdown
    assert "### Vehicle Speed Clip Gates" in markdown
    assert "Vehicle display coverage" in markdown
    assert "Safe vehicle display coverage" in markdown
    assert "Hidden ID-switch risk count" in markdown
    assert "3D calibration region quality" in markdown
    assert (
        "| clip.mp4 | 0.99 | False | 0.00 | 0.00 | 0 | 0 | 0 | "
        "review | 40.00 km/h |"
    ) in markdown
    assert "Weak-scale tracks" in markdown
    assert "| clip.mp4 | yes | yes | yes | yes | yes | yes | yes |" in markdown


def test_benchmark_summary_recomputes_vehicle_aggregate_from_result_audits() -> None:
    payload = {
        "regression_set": {
            "aggregate_min_coverage": 0.995,
            "clip_min_coverage": 0.995,
            "max_car_speed_kmh": 160.0,
        },
        "summary": {
            "mps_available": False,
            "mps_built": True,
            "vehicle_speed_aggregate": {
                "vehicle_track_samples": 1,
                "vehicle_display_coverage": 0.0,
            },
        },
        "results": [
            {
                "status": "ok",
                "clip": "clip.mp4",
                "scene_profile": {"name": "road"},
                "calibration": {
                    "source": "video_manual_preset",
                    "quality": "excellent",
                    "position_rmse_floor_m": 0.4,
                    "scale_uncertainty_pct": 2.5,
                },
                "sensitivity": {"space_mean_speed_band_kmh": [38.0, 42.0]},
                "effective_processing_fps": 12.0,
                "final_report": {
                    "active_tracks": [],
                    "regional_people_count": {"people_count": 0},
                    "infrastructure_semantics": {"traffic_light_count": 0},
                    "traffic_flow": {
                        "flow_q_veh_per_hour": None,
                        "density_k_veh_per_km": None,
                        "space_mean_speed_kmh": None,
                        "congestion_level": "unknown",
                    },
                    "safety_metrics": {
                        "risk_level": "unknown",
                        "min_time_to_collision_sec": None,
                        "min_time_headway_sec": None,
                    },
                },
                "vehicle_speed_audit": {
                    "clip": "clip.mp4",
                    "vehicle_track_samples": 100,
                    "displayable_vehicle_track_samples": 100,
                    "vehicle_display_coverage": 1.0,
                    "max_speed_by_class": {"car": 40.0},
                },
            },
        ],
    }

    summary = build_benchmark_summary(payload)

    assert summary["vehicle_speed_aggregate"]["vehicle_track_samples"] == 100
    assert summary["vehicle_speed_aggregate"]["vehicle_display_coverage"] == 1.0
    assert summary["vehicle_speed_aggregate"]["dense_city_acceptance_min_coverage"] == 0.995


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
