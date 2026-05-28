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
    assert context.physical_state["traffic_flow"]["congestion_level"]
    assert context.motion_routes[0]["category"] == "high_inertia_dynamic"
    assert context.motion_routes[0]["speed_confidence"] is not None
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


def test_context_assembler_exports_prompt_payload() -> None:
    context = DynamicContextAssembler().assemble(generate_demo_report(), scene_tags=["demo"])

    payload = context.to_prompt_payload()

    assert payload["context_version"] == "1.0"
    assert payload["scene"]["scene_tags"] == ["demo"]
    assert payload["physical_state"]["zones"] == ["main_gate"]
