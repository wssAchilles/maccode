from __future__ import annotations

import json
from pathlib import Path

from scripts.rebuild_vehicle_speed_audits import (
    collect_result_paths,
    rebuild_vehicle_speed_audits,
)


def _result_payload() -> dict[str, object]:
    final_report = {
        "frame_index": 2,
        "active_tracks": [
            {
                "tracker_id": 1,
                "class_id": 2,
                "class_name": "car",
                "speed_kmh": 42.0,
                "speed_confidence": 0.8,
                "speed_uncertainty_kmh": 2.0,
                "physics_valid": True,
            },
        ],
        "regional_people_count": {"people_count": 0},
        "infrastructure_semantics": {"traffic_light_count": 0, "static_context": []},
        "traffic_flow": {
            "space_mean_speed_kmh": 42.0,
            "flow_q_veh_per_hour": 100.0,
            "density_k_veh_per_km": 12.0,
            "congestion_level": "free_flow",
        },
        "safety_metrics": {
            "risk_level": "low",
            "min_time_to_collision_sec": None,
            "min_time_headway_sec": None,
        },
    }
    return {
        "clip": "063_dense_city_traffic_4k_elevated_0300s_30s.mp4",
        "status": "ok",
        "frame_stride": 1,
        "max_frames": 2,
        "processed_frame_estimate": 2,
        "effective_processing_fps": 30.0,
        "scene_profile": {"name": "dense_city_traffic_4k"},
        "calibration": {
            "source": "video_manual_preset",
            "quality": "trusted",
            "position_rmse_floor_m": 0.25,
            "scale_uncertainty_pct": 3.0,
        },
        "sensitivity": {"space_mean_speed_band_kmh": [40.0, 44.0]},
        "final_report": final_report,
        "frame_reports": [
            {
                "frame_index": 1,
                "timestamp_sec": 0.0,
                "active_tracks": [
                    {
                        "tracker_id": 1,
                        "class_id": 2,
                        "class_name": "car",
                        "speed_kmh": 40.0,
                        "speed_confidence": 0.8,
                        "speed_uncertainty_kmh": 2.0,
                        "physics_valid": True,
                        "measurement_source": "vehicle_bottom_center",
                    },
                ],
            },
            final_report,
        ],
    }


def test_collect_result_paths_skips_summary_and_speed_audits(tmp_path: Path) -> None:
    keep = tmp_path / "clip.json"
    keep.write_text("{}", encoding="utf-8")
    (tmp_path / "summary.json").write_text("{}", encoding="utf-8")
    (tmp_path / "clip_processed_speed_audit.json").write_text("{}", encoding="utf-8")

    assert collect_result_paths([tmp_path]) == [keep]


def test_rebuild_vehicle_speed_audits_writes_lightweight_outputs(tmp_path: Path) -> None:
    source = tmp_path / "source"
    output = tmp_path / "output"
    source.mkdir()
    clip_json = source / "063_dense_city_traffic_4k_elevated_0300s_30s.json"
    clip_json.write_text(json.dumps(_result_payload()), encoding="utf-8")
    (source / "summary.json").write_text("{}", encoding="utf-8")

    payload = rebuild_vehicle_speed_audits(
        [source],
        output_dir=output,
        speed_ground_truth_dir=tmp_path / "missing_gt",
        source_commit_value="abc123",
    )

    assert payload["summary"]["successful_clips"] == 1
    assert payload["summary"]["vehicle_speed_aggregate"]["vehicle_track_samples"] == 2
    assert (output / "summary.json").exists()
    assert (output / "benchmark_summary.json").exists()
    assert (
        output
        / "vehicle_speed_diagnostics"
        / "063_dense_city_traffic_4k_elevated_0300s_30s.json"
    ).exists()
    lightweight = json.loads(
        (output / "063_dense_city_traffic_4k_elevated_0300s_30s_reaudit.json").read_text(
            encoding="utf-8",
        ),
    )
    assert "frame_reports" not in lightweight
    assert lightweight["vehicle_speed_audit"]["report_schema_version"] == "vehicle_speed_report_v3"
    assert lightweight["vehicle_speed_audit"]["contact_point_source_counts"][
        "vehicle_bottom_center"
    ] == 1


def test_rebuild_vehicle_speed_audits_uses_annotated_final_report(tmp_path: Path) -> None:
    source = tmp_path / "source"
    output = tmp_path / "output"
    source.mkdir()
    payload = _result_payload()
    payload["frame_reports"][1]["active_tracks"][0]["measurement_source"] = "bbox_center"
    payload["frame_reports"][1]["active_tracks"][0]["speed_confidence"] = 0.9
    payload["frame_reports"][1]["active_tracks"][0]["speed_uncertainty_kmh"] = 3.0
    clip_json = source / "063_dense_city_traffic_4k_elevated_0300s_30s.json"
    clip_json.write_text(json.dumps(payload), encoding="utf-8")

    rebuild_vehicle_speed_audits(
        [source],
        output_dir=output,
        speed_ground_truth_dir=tmp_path / "missing_gt",
        source_commit_value="abc123",
    )

    lightweight = json.loads(
        (output / "063_dense_city_traffic_4k_elevated_0300s_30s_reaudit.json").read_text(
            encoding="utf-8",
        ),
    )
    final_track = lightweight["final_report"]["active_tracks"][0]

    assert final_track["bbox_center_fallback"] is True
    assert final_track["physics_valid"] is False
    assert final_track["speed_display_hidden"] is True
    assert lightweight["vehicle_speed_audit"]["displayable_vehicle_track_samples"] == 1
