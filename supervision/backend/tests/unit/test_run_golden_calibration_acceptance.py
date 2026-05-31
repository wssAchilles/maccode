from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import scripts.run_golden_calibration_acceptance as pipeline


def test_run_pipeline_writes_final_audit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    clips = [
        "026_complex_signal_day_wide_0115s_30s.mp4",
        "042_pedestrian_crowd_high_view_0270s_30s.mp4",
        "054_dense_city_traffic_4k_elevated_0030s_30s.mp4",
        "058_dense_city_traffic_4k_elevated_0150s_30s.mp4",
    ]
    artifact_paths = {}
    for clip in clips:
        clip_dir = tmp_path / clip
        clip_dir.mkdir()
        artifact_paths[clip] = {
            "qa_image": clip_dir / "qa.jpg",
            "processed_mp4": clip_dir / "processed.mp4",
            "math_model_card_md": clip_dir / "math.md",
            "frame_report_json": clip_dir / "report.json",
        }
        for path in artifact_paths[clip].values():
            path.write_text("artifact", encoding="utf-8")

    def fake_build_qa_summary(**kwargs: Any) -> dict[str, Any]:
        output_dir = kwargs["output_dir"]
        output_dir.mkdir(parents=True)
        summary = {
            "clip_count": 4,
            "trusted_count": 4,
            "clips": [
                {
                    "clip": clip,
                    "calibration_source": "video_manual_preset",
                    "calibration_trusted": True,
                    "declared_trusted": True,
                    "validation_max_error_px": 6.0,
                    "world_to_pixel_rmse_px": 1.0,
                    "point_count": 8,
                    "validation_segment_count": 2,
                    "independent_validation_segment_count": 2,
                    "grid_rendered": True,
                    "qa_image": str(artifact_paths[clip]["qa_image"]),
                }
                for clip in clips
            ],
        }
        (output_dir / "calibration_qa_summary.json").write_text(
            json.dumps(summary),
            encoding="utf-8",
        )
        return summary

    def fake_build_acceptance_table(**kwargs: Any) -> dict[str, Any]:
        output_dir = kwargs["output_dir"]
        output_dir.mkdir(parents=True)
        acceptance = {
            "clip_count": 4,
            "trusted_count": 4,
            "clips": [
                {
                    "clip": clip,
                    "calibration_source": "video_manual_preset",
                    "calibration_trusted": True,
                    "calibration_pipeline_consistent": True,
                    "validation_max_error_px": 6.0,
                    "independent_validation_segment_count": 2,
                        "homography_grid_rendered": True,
                        "point_count": 8,
                        "has_scale_prior": True,
                        "has_profile_notes": True,
                        "has_road_plane_polygon_pixel": True,
                        "has_road_plane_polygon_world": True,
                        "qa_image": str(artifact_paths[clip]["qa_image"]),
                        "processed_mp4": str(artifact_paths[clip]["processed_mp4"]),
                        "math_model_card_md": str(artifact_paths[clip]["math_model_card_md"]),
                    "frame_report_json": str(artifact_paths[clip]["frame_report_json"]),
                }
                for clip in clips
            ],
        }
        (output_dir / "golden_acceptance_table.json").write_text(
            json.dumps(acceptance),
            encoding="utf-8",
        )
        return acceptance

    def fake_build_readiness_report(**kwargs: Any) -> dict[str, Any]:
        output_dir = kwargs["output_dir"]
        output_dir.mkdir(parents=True)
        return {
            "clip_count": 4,
            "trusted_count": 4,
            "ready_for_defense_count": 4,
        }

    monkeypatch.setattr(pipeline, "build_qa_summary", fake_build_qa_summary)
    monkeypatch.setattr(pipeline, "build_acceptance_table", fake_build_acceptance_table)
    monkeypatch.setattr(pipeline, "build_readiness_report", fake_build_readiness_report)

    result = pipeline.run_pipeline(
        input_dir=tmp_path,
        calibration_presets=tmp_path / "calibration.yaml",
        camera_profiles=tmp_path / "camera.yaml",
        analysis_summary=tmp_path / "summary.json",
        analysis_output_dir=tmp_path / "analysis",
        qa_output_dir=tmp_path / "qa",
        acceptance_output_dir=tmp_path / "acceptance",
        readiness_output_dir=tmp_path / "readiness",
        audit_output_dir=tmp_path / "audit",
        clips=clips,
        frame_index=1,
        project_root=tmp_path,
    )

    assert result["audit"]["all_defense_ready"] is True
    assert (tmp_path / "audit" / "golden_calibration_audit.json").exists()
    assert (tmp_path / "audit" / "golden_calibration_audit.md").exists()


def test_run_pipeline_can_refresh_real_analysis_before_acceptance(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    called: dict[str, bool] = {"analysis": False}
    clips = [
        "026_complex_signal_day_wide_0115s_30s.mp4",
        "042_pedestrian_crowd_high_view_0270s_30s.mp4",
        "054_dense_city_traffic_4k_elevated_0030s_30s.mp4",
        "058_dense_city_traffic_4k_elevated_0150s_30s.mp4",
    ]

    def fake_run_real_analysis(**kwargs: Any) -> Path:
        called["analysis"] = True
        output_dir = kwargs["output_dir"]
        output_dir.mkdir(parents=True)
        summary_path = output_dir / "summary.json"
        summary_path.write_text(json.dumps({"results": []}), encoding="utf-8")
        return summary_path

    def fake_build_qa_summary(**kwargs: Any) -> dict[str, Any]:
        output_dir = kwargs["output_dir"]
        output_dir.mkdir(parents=True)
        (output_dir / "calibration_qa_summary.json").write_text("{}", encoding="utf-8")
        return {"clip_count": 4, "trusted_count": 0, "clips": []}

    def fake_build_acceptance_table(**kwargs: Any) -> dict[str, Any]:
        output_dir = kwargs["output_dir"]
        output_dir.mkdir(parents=True)
        acceptance = {"clip_count": 0, "trusted_count": 0, "clips": []}
        (output_dir / "golden_acceptance_table.json").write_text(
            json.dumps(acceptance),
            encoding="utf-8",
        )
        return acceptance

    def fake_build_readiness_report(**kwargs: Any) -> dict[str, Any]:
        output_dir = kwargs["output_dir"]
        output_dir.mkdir(parents=True)
        return {"clip_count": 0, "trusted_count": 0, "ready_for_defense_count": 0}

    monkeypatch.setattr(pipeline, "run_real_analysis", fake_run_real_analysis)
    monkeypatch.setattr(pipeline, "build_qa_summary", fake_build_qa_summary)
    monkeypatch.setattr(pipeline, "build_acceptance_table", fake_build_acceptance_table)
    monkeypatch.setattr(pipeline, "build_readiness_report", fake_build_readiness_report)
    monkeypatch.setattr(pipeline, "write_math_model_cards", lambda **_: None)

    pipeline.run_pipeline(
        input_dir=tmp_path,
        calibration_presets=tmp_path / "calibration.yaml",
        camera_profiles=tmp_path / "camera.yaml",
        analysis_summary=tmp_path / "old_summary.json",
        analysis_output_dir=tmp_path / "analysis",
        qa_output_dir=tmp_path / "qa",
        acceptance_output_dir=tmp_path / "acceptance",
        readiness_output_dir=tmp_path / "readiness",
        audit_output_dir=tmp_path / "audit",
        clips=clips,
        frame_index=1,
        project_root=tmp_path,
        run_analysis=True,
    )

    assert called["analysis"] is True
