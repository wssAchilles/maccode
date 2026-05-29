from __future__ import annotations

from application.services.context_assembler import DynamicContextAssembler
from scripts.generate_demo_report import generate_demo_report


def test_context_assembler_builds_physical_summary_and_motion_routes() -> None:
    context = DynamicContextAssembler().assemble(
        generate_demo_report(),
        location_label="学校门口",
        scene_tags=["school_zone", "rain"],
    )

    assert context.scene["location_label"] == "学校门口"
    assert context.scene["scene_tags"] == ["school_zone", "rain"]
    assert context.physical_state["total_in"] == 1
    assert context.physical_state["active_tracks"] == 1
    assert context.physical_state["calibration_quality"] == "excellent"
    assert context.physical_state["calibration_diagnostics"]["inlier_count"] >= 4
    assert (
        context.physical_state["calibration_diagnostics"]["model_reference"]
        == "Model 1 + Model 3 + Model 6 + Model 10"
    )
    assert (
        context.physical_state["homography_grid"]["generated_from"]
        == "inverse_homography_projection"
    )
    assert context.physical_state["traffic_flow"]["congestion_level"]
    assert context.physical_state["regional_people_count"]["people_count"] == 0
    assert context.physical_state["infrastructure_semantics"]["traffic_light_state"]
    assert context.physical_state["safety_metrics"]["risk_level"] == "nominal"
    assert context.motion_routes[0]["category"] == "high_inertia_dynamic"
    assert context.motion_routes[0]["speed_confidence"] is not None
    assert context.motion_routes[0]["ground_position_m"]["x"] is not None
    assert context.motion_routes[0]["velocity_mps"]["x"] is not None
    assert context.motion_routes[0]["speed_confidence_interval_kmh"] is not None
    assert "use_physical_json_only" in context.decision_constraints


def test_context_assembler_flags_school_zone_speeding_risk() -> None:
    report = generate_demo_report()
    report["active_tracks"][0]["speed_kmh"] = 92.0

    context = DynamicContextAssembler(speed_limit_kmh=80.0).assemble(
        report,
        location_label="学校门口",
        scene_tags=["school_zone"],
    )

    assert context.risk_signals[0]["type"] == "speeding_near_sensitive_area"
    assert context.risk_signals[0]["severity"] == "high"
    assert context.risk_signals[0]["tracker_id"] == 1


def test_context_assembler_ignores_unphysical_speed_values() -> None:
    report = generate_demo_report()
    report["active_tracks"][0]["speed_kmh"] = 180.0
    report["active_tracks"][0]["physics_valid"] = False
    report["active_tracks"][0]["quality_label"] = "rejected"

    context = DynamicContextAssembler(speed_limit_kmh=30.0).assemble(
        report,
        location_label="学校门口",
        scene_tags=["school_zone"],
    )

    assert context.physical_state["avg_speed_kmh"] is None
    assert not any(
        signal["type"] == "speeding_near_sensitive_area"
        for signal in context.risk_signals
    )


def test_context_assembler_exports_prompt_payload() -> None:
    context = DynamicContextAssembler().assemble(generate_demo_report(), scene_tags=["demo"])

    payload = context.to_prompt_payload()

    assert payload["context_version"] == "1.0"
    assert payload["scene"]["scene_tags"] == ["demo"]
    assert payload["physical_state"]["zones"] == ["main_gate"]


def test_context_assembler_flags_safety_metrics_risk() -> None:
    report = generate_demo_report()
    report["safety_metrics"] = {
        "risk_level": "critical",
        "min_time_headway_sec": 0.9,
        "min_time_to_collision_sec": 1.7,
    }

    context = DynamicContextAssembler().assemble(report)

    assert any(
        signal["type"] == "short_headway_or_collision_risk"
        and signal["severity"] == "high"
        for signal in context.risk_signals
    )


def test_context_assembler_exports_red_light_and_crowd_density_risks() -> None:
    report = generate_demo_report()
    report["regional_people_count"] = {
        "region_name": "hospital_gate",
        "people_count": 220,
        "direct_detection_count": 180,
        "integrated_people_count": 219.6,
        "density_people_per_sqm": 2.8,
        "estimation_method": "density_field_integral",
        "density_integral_triggered": True,
        "crowding_level": "critical",
    }
    report["infrastructure_semantics"] = {
        "traffic_light_count": 1,
        "stop_sign_count": 0,
        "traffic_light_state": "red",
        "violation_on_crosswalk": True,
        "red_light_violation_candidate_track_ids": [12],
        "dynamic_vehicle_count": 4,
    }
    report["safety_metrics"] = {
        "risk_level": "critical",
        "speeding_track_ids": [12],
        "red_light_violation_track_ids": [12],
    }

    context = DynamicContextAssembler().assemble(report, location_label="医院门口")

    assert any(signal["type"] == "red_light_violation" for signal in context.risk_signals)
    assert any(signal["type"] == "critical_crowd_density" for signal in context.risk_signals)
