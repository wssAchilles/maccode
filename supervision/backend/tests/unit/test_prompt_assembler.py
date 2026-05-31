from __future__ import annotations

from application.services.context_assembler import DynamicContextAssembler
from infrastructure.cognition.prompts import PromptAssembler
from scripts.generate_demo_report import generate_demo_report


def test_prompt_assembler_splices_atomic_context_from_scene_tags() -> None:
    frame_report = generate_demo_report()
    dynamic_context = DynamicContextAssembler().assemble(
        frame_report,
        location_label="学校门口",
        scene_tags=["school_zone", "rain", "waterlogging"],
    )

    messages = PromptAssembler().build_messages(
        frame_report,
        dynamic_context.to_prompt_payload(),
        location_label="学校门口",
        scene_tags=["school_zone", "rain", "waterlogging"],
    )

    assert [message["role"] for message in messages] == ["system", "user"]
    assert "Model 1/8" in messages[0]["content"]
    assert "学校门口" in messages[1]["content"]
    assert "雨天" in messages[1]["content"]
    assert "积水" in messages[1]["content"]
    assert "dynamic_context" in messages[1]["content"]
    assert "FrameReport" in messages[1]["content"]
    assert "人性化解释规则" in messages[0]["content"]
    assert "不要把物理量名称直接堆给用户" in messages[0]["content"]


def test_prompt_assembler_sanitizes_invalid_physics_speed() -> None:
    frame_report = generate_demo_report()
    frame_report["active_tracks"].append(
        {
            "tracker_id": 999,
            "class_id": 2,
            "class_name": "car",
            "speed_kmh": 188.8,
            "speed_uncertainty_kmh": 7.5,
            "speed_confidence_interval_kmh": [181.3, 196.3],
            "physics_valid": False,
        }
    )
    dynamic_context = DynamicContextAssembler().assemble(frame_report)

    messages = PromptAssembler().build_messages(
        frame_report,
        dynamic_context.to_prompt_payload(),
    )
    user_prompt = messages[1]["content"]

    assert '"tracker_id": 999' in user_prompt
    assert '"speed_kmh": null' in user_prompt
    assert "188.8" not in user_prompt
    assert "196.3" not in user_prompt


def test_prompt_assembler_sanitizes_untrusted_calibration_speed() -> None:
    frame_report = generate_demo_report()
    frame_report["calibration_diagnostics"]["calibration_trusted"] = False
    frame_report["homography_grid"] = None
    frame_report["active_tracks"][0]["speed_kmh"] = 144.4
    frame_report["active_tracks"][0]["speed_confidence_interval_kmh"] = [139.0, 149.0]
    frame_report["active_tracks"][0]["physics_valid"] = True
    frame_report["traffic_flow"]["space_mean_speed_kmh"] = 88.8
    frame_report["safety_metrics"] = {
        "speeding_track_ids": [1],
        "min_time_headway_sec": 0.4,
        "min_time_to_collision_sec": 1.1,
    }
    dynamic_context = DynamicContextAssembler().assemble(frame_report)

    messages = PromptAssembler().build_messages(
        frame_report,
        dynamic_context.to_prompt_payload(),
    )
    user_prompt = messages[1]["content"]

    assert '"calibration_trusted": false' in user_prompt
    assert '"speed_kmh": null' in user_prompt
    assert '"space_mean_speed_kmh": null' in user_prompt
    assert '"speeding_track_ids": []' in user_prompt
    assert "144.4" not in user_prompt
    assert "149.0" not in user_prompt
    assert "88.8" not in user_prompt
