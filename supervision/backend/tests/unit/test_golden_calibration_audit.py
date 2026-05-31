from __future__ import annotations

from pathlib import Path

from scripts.audit_golden_calibration import audit_acceptance_table


def _artifact_paths(tmp_path: Path) -> dict[str, str]:
    paths = {
        "qa_image": tmp_path / "qa.jpg",
        "processed_mp4": tmp_path / "processed.mp4",
        "math_model_card_md": tmp_path / "math_model_card.md",
        "frame_report_json": tmp_path / "frame_report.json",
    }
    for path in paths.values():
        path.write_text("artifact", encoding="utf-8")
    return {key: str(path) for key, path in paths.items()}


def _row(tmp_path: Path, clip: str, *, trusted: bool = True) -> dict[str, object]:
    return {
        "clip": clip,
        "calibration_source": "video_manual_preset",
        "calibration_trusted": trusted,
        "provenance_trusted": True,
        "provenance_issues": [],
        "calibration_pipeline_consistent": True,
        "validation_max_error_px": 6.0,
        "independent_validation_segment_count": 2,
        "homography_grid_rendered": trusted,
        "point_count": 8,
        "has_scale_prior": True,
        "has_profile_notes": True,
        "has_road_plane_polygon_pixel": True,
        "has_road_plane_polygon_world": True,
        **_artifact_paths(tmp_path / clip),
    }


def test_audit_accepts_all_four_trusted_golden_clips(tmp_path: Path) -> None:
    clips = [
        "026_complex_signal_day_wide_0115s_30s.mp4",
        "042_pedestrian_crowd_high_view_0270s_30s.mp4",
        "054_dense_city_traffic_4k_elevated_0030s_30s.mp4",
        "058_dense_city_traffic_4k_elevated_0150s_30s.mp4",
    ]
    for clip in clips:
        (tmp_path / clip).mkdir()
    payload = {
        "clips": [_row(tmp_path, clip) for clip in clips],
    }

    audit = audit_acceptance_table(payload, project_root=tmp_path)

    assert audit["all_defense_ready"] is True
    assert audit["defense_ready_count"] == 4
    assert audit["global_issues"] == []


def test_audit_rejects_untrusted_grid_and_missing_independent_segments(
    tmp_path: Path,
) -> None:
    clip = "026_complex_signal_day_wide_0115s_30s.mp4"
    (tmp_path / clip).mkdir()
    row = _row(tmp_path, clip, trusted=False)
    row["homography_grid_rendered"] = True
    row["independent_validation_segment_count"] = 0
    payload = {"clips": [row]}

    audit = audit_acceptance_table(payload, project_root=tmp_path)

    assert audit["all_defense_ready"] is False
    clip_audit = audit["clips"][0]
    assert "untrusted calibration rendered Homography Grid" in clip_audit["issues"]
    assert "not enough independent validation segments" in clip_audit["warnings"]


def test_audit_rejects_missing_sampling_evidence(tmp_path: Path) -> None:
    clip = "026_complex_signal_day_wide_0115s_30s.mp4"
    (tmp_path / clip).mkdir()
    row = _row(tmp_path, clip)
    row["point_count"] = 6
    row["has_scale_prior"] = False
    row["has_road_plane_polygon_pixel"] = False
    payload = {"clips": [row]}

    audit = audit_acceptance_table(payload, project_root=tmp_path)

    assert audit["all_defense_ready"] is False
    clip_audit = audit["clips"][0]
    assert "missing scale_prior meter anchor" in clip_audit["issues"]
    assert "missing road_plane_polygon_pixel" in clip_audit["issues"]
    assert any("requires 8-10 manual control points" in issue for issue in clip_audit["issues"])


def test_audit_rejects_visual_prior_provenance(tmp_path: Path) -> None:
    clip = "026_complex_signal_day_wide_0115s_30s.mp4"
    (tmp_path / clip).mkdir()
    row = _row(tmp_path, clip)
    row["provenance_trusted"] = False
    row["provenance_issues"] = ["annotation_method is not manual/survey provenance"]
    payload = {"clips": [row]}

    audit = audit_acceptance_table(payload, project_root=tmp_path)

    assert audit["all_defense_ready"] is False
    assert "annotation_method is not manual/survey provenance" in audit["clips"][0]["issues"]
