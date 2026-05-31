from __future__ import annotations

from scripts.build_calibration_readiness_report import (
    camera_profile_reuse_target,
    readiness_level,
    required_actions,
)


def test_readiness_actions_reject_high_validation_error() -> None:
    clip = "026_complex_signal_day_wide_0115s_30s.mp4"
    row = {
        "clip": clip,
        "calibration_source": "video_manual_preset",
        "calibration_trusted": False,
        "declared_trusted": False,
        "homography_grid_rendered": False,
        "point_count": 6,
        "validation_segment_count": 2,
        "validation_max_error_px": 964.3,
        "calibration_pipeline_consistent": True,
    }

    assert readiness_level(row) == "needs_manual_refinement"
    actions = required_actions(row)
    assert any("exceeds 15px gate" in action for action in actions)
    assert any("calibration_trusted=false" in action for action in actions)
    assert camera_profile_reuse_target(clip) == "jackson_hole_signal_camera"


def test_readiness_level_accepts_trusted_grid_with_ideal_validation() -> None:
    row = {
        "calibration_trusted": True,
        "homography_grid_rendered": True,
        "validation_max_error_px": 4.0,
    }

    assert readiness_level(row) == "trusted_ideal"
