from __future__ import annotations

import json
from pathlib import Path

from scripts.build_vehicle_3d_speed_qa import build_vehicle_3d_speed_qa


def test_build_vehicle_3d_speed_qa_writes_json_and_markdown(tmp_path: Path) -> None:
    source = tmp_path / "results"
    output = tmp_path / "qa"
    source.mkdir()
    result_path = source / "063_dense_city.json"
    result_path.write_text(
        json.dumps(
            {
                "clip": "063_dense_city.mp4",
                "frame_reports": [
                    {
                        "frame_index": 1,
                        "calibration_diagnostics": {
                            "calibration_3d_diagnostics": {
                                "calibration_source": "vehicle_3d_prior_pnp",
                                "calibration_quality": "stable",
                                "calibration_trusted": True,
                                "quality_issues": [],
                            },
                        },
                        "active_tracks": [
                            {
                                "tracker_id": 1,
                                "class_id": 2,
                                "class_name": "car",
                                "xyxy": [0.0, 0.0, 100.0, 50.0],
                                "local_scale_factor": 0.0185,
                                "ground_y_m": 5.0,
                                "plane_id": "lane_1",
                                "speed_kmh": 40.0,
                                "physics_valid": True,
                            },
                            {
                                "tracker_id": 2,
                                "class_id": 2,
                                "class_name": "car",
                                "xyxy": [0.0, 0.0, 100.0, 50.0],
                                "local_scale_factor": 0.0185,
                                "ground_y_m": 20.0,
                                "plane_id": "lane_1",
                                "speed_kmh": 42.0,
                                "physics_valid": True,
                            },
                        ],
                    },
                ],
            },
        ),
        encoding="utf-8",
    )

    payload = build_vehicle_3d_speed_qa([source], output_dir=output)

    assert payload["clip_count"] == 1
    assert payload["aggregate"]["calibration_3d_available_count"] == 1
    assert payload["aggregate"]["review_clip_count"] == 0
    assert payload["clips"][0]["calibration_3d_source"] == "vehicle_3d_prior_pnp"
    assert payload["clips"][0]["calibration_3d_quality"] == "stable"
    assert abs(payload["clips"][0]["bbox_size_consistency_error"]) < 1e-9
    assert payload["clips"][0]["recommended_action"] == "none"
    assert (output / "vehicle_3d_speed_qa.json").exists()
    assert "Vehicle 3D Speed QA" in (output / "vehicle_3d_speed_qa.md").read_text(
        encoding="utf-8",
    )


def test_build_vehicle_3d_speed_qa_reports_missing_displayable_tracks(
    tmp_path: Path,
) -> None:
    source = tmp_path / "results"
    output = tmp_path / "qa"
    source.mkdir()
    (source / "063_dense_city.json").write_text(
        json.dumps(
            {
                "clip": "063_dense_city.mp4",
                "frame_reports": [{"frame_index": 1, "active_tracks": []}],
            },
        ),
        encoding="utf-8",
    )

    payload = build_vehicle_3d_speed_qa([source], output_dir=output)

    assert payload["clips"][0]["vehicle_3d_scale_sanity_available"] is False
    assert (
        payload["clips"][0]["recommended_action"]
        == "collect_vehicle_tracks_for_scale_sanity"
    )


def test_build_vehicle_3d_speed_qa_reports_missing_3d_priors(
    tmp_path: Path,
) -> None:
    source = tmp_path / "results"
    output = tmp_path / "qa"
    source.mkdir()
    (source / "063_dense_city.json").write_text(
        json.dumps(
            {
                "clip": "063_dense_city.mp4",
                "frame_reports": [
                    {
                        "frame_index": 1,
                        "active_tracks": [
                            {
                                "tracker_id": 1,
                                "class_id": 2,
                                "class_name": "car",
                                "xyxy": [0.0, 0.0, 100.0, 50.0],
                                "local_scale_factor": 0.0185,
                                "ground_y_m": 5.0,
                                "plane_id": "lane_1",
                                "speed_kmh": 40.0,
                                "physics_valid": True,
                            },
                            {
                                "tracker_id": 2,
                                "class_id": 2,
                                "class_name": "car",
                                "xyxy": [0.0, 0.0, 100.0, 50.0],
                                "local_scale_factor": 0.0185,
                                "ground_y_m": 20.0,
                                "plane_id": "lane_1",
                                "speed_kmh": 40.5,
                                "physics_valid": True,
                            },
                        ],
                    },
                ],
            },
        ),
        encoding="utf-8",
    )

    payload = build_vehicle_3d_speed_qa([source], output_dir=output)

    assert payload["clips"][0]["vehicle_3d_scale_sanity_available"] is True
    assert payload["clips"][0]["calibration_3d_available"] is False
    assert (
        payload["clips"][0]["recommended_action"]
        == "add_vehicle_3d_priors_or_bbox_observations_for_offline_qa"
    )


def test_build_vehicle_3d_speed_qa_flags_review_regions(
    tmp_path: Path,
) -> None:
    source = tmp_path / "results"
    output = tmp_path / "qa"
    source.mkdir()
    (source / "063_dense_city.json").write_text(
        json.dumps(
            {
                "clip": "063_dense_city.mp4",
                "frame_reports": [
                    {
                        "frame_index": 1,
                        "active_tracks": [
                            {
                                "tracker_id": 1,
                                "class_id": 2,
                                "class_name": "car",
                                "xyxy": [0.0, 0.0, 100.0, 50.0],
                                "local_scale_factor": 0.05,
                                "ground_y_m": 5.0,
                                "plane_id": "lane_1",
                                "speed_kmh": 40.0,
                                "physics_valid": True,
                            },
                            {
                                "tracker_id": 2,
                                "class_id": 2,
                                "class_name": "car",
                                "xyxy": [0.0, 0.0, 100.0, 50.0],
                                "local_scale_factor": 0.05,
                                "ground_y_m": 20.0,
                                "plane_id": "lane_1",
                                "speed_kmh": 40.5,
                                "physics_valid": True,
                            },
                        ],
                    },
                ],
            },
        ),
        encoding="utf-8",
    )

    payload = build_vehicle_3d_speed_qa([source], output_dir=output)

    assert payload["clips"][0]["calibration_region_quality"] == "review"
    assert (
        payload["clips"][0]["recommended_action"]
        == "increase_region_uncertainty_or_add_gt_speed_samples"
    )
