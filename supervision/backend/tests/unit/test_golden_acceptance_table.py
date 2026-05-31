from __future__ import annotations

from pathlib import Path

from scripts.build_golden_acceptance_table import build_row


def test_acceptance_row_flags_qa_analysis_calibration_mismatch(tmp_path: Path) -> None:
    analysis_json = tmp_path / "clip.json"
    analysis_json.write_text("{}")
    analysis_row = {
        "clip": "clip.mp4",
        "calibration": {"source": "scene_profile_preset", "trusted": False},
        "processed_video": {"path": str(tmp_path / "clip_processed.mp4")},
        "metadata": {"frame_count": 10},
        "final_report": {"active_tracks": [], "total_in": 0, "total_out": 0},
    }
    qa_row = {
        "clip": "clip.mp4",
        "calibration_source": "video_manual_preset",
        "calibration_trusted": True,
        "declared_trusted": True,
        "validation_max_error_px": 4.0,
        "world_to_pixel_rmse_px": 1.0,
        "point_count": 6,
        "validation_segment_count": 2,
        "grid_rendered": True,
        "qa_image": str(tmp_path / "qa.jpg"),
    }

    row = build_row(qa_row, analysis_row, tmp_path)

    assert row["acceptance_status"] == "pipeline_mismatch"
    assert row["calibration_pipeline_consistent"] is False
    assert row["analysis_calibration_source"] == "scene_profile_preset"
