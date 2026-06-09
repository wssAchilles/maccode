from __future__ import annotations

import argparse
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml
from scripts import run_vehicle_speed_regression
from scripts.run_vehicle_speed_regression import (
    available_clips,
    build_regression_summary,
    load_regression_set,
    run_regression,
    selected_clip_names,
)


def test_loads_default_dense_city_vehicle_speed_regression_set() -> None:
    regression = load_regression_set(
        Path("data/tests/vehicle_speed_regression.yaml"),
        None,
    )

    assert regression["name"] == "dense_city_4k_053_065"
    assert regression["profile_id"] == "dense_city_4k_camera"
    assert regression["aggregate_min_coverage"] == 0.993
    assert "063_dense_city_traffic_4k_elevated_0300s_30s.mp4" in regression["clips"]
    assert "065_dense_city_traffic_4k_elevated_0360s_30s.mp4" in regression["clips"]


def test_available_clips_reports_missing_without_failing(tmp_path: Path) -> None:
    present = tmp_path / "063_dense_city_traffic_4k_elevated_0300s_30s.mp4"
    present.write_bytes(b"mp4")

    selected, missing = available_clips(
        tmp_path,
        [
            present.name,
            "064_dense_city_traffic_4k_elevated_0330s_30s.mp4",
        ],
    )

    assert selected == [present]
    assert missing == ["064_dense_city_traffic_4k_elevated_0330s_30s.mp4"]


def test_unknown_vehicle_speed_regression_set_fails() -> None:
    with pytest.raises(ValueError, match="unknown vehicle speed regression set"):
        load_regression_set(Path("data/tests/vehicle_speed_regression.yaml"), "missing")


def test_selected_clip_names_filters_to_requested_regression_order() -> None:
    clips = [
        "063_dense_city_traffic_4k_elevated_0300s_30s.mp4",
        "064_dense_city_traffic_4k_elevated_0330s_30s.mp4",
    ]

    assert selected_clip_names(clips, [clips[1]]) == [clips[1]]
    assert selected_clip_names(clips, None) == clips


def test_selected_clip_names_rejects_clips_outside_regression_set() -> None:
    clips = ["063_dense_city_traffic_4k_elevated_0300s_30s.mp4"]

    with pytest.raises(ValueError, match="not in the vehicle speed regression set"):
        selected_clip_names(clips, ["unrelated.mp4"])


def test_regression_summary_uses_thresholds_from_regression_config() -> None:
    summary = build_regression_summary(
        [
            {
                "status": "ok",
                "clip": "063_dense_city.mp4",
                "final_report": {
                    "active_tracks": [
                        {
                            "speed_kmh": 40.0,
                            "physics_valid": True,
                            "speed_confidence": 0.8,
                        },
                    ],
                },
                "vehicle_speed_audit": {
                    "clip": "063_dense_city.mp4",
                    "vehicle_track_samples": 1000,
                    "displayable_vehicle_track_samples": 994,
                    "vehicle_display_coverage": 0.994,
                    "max_speed_by_class": {"car": 80.0},
                },
            },
        ],
        {
            "aggregate_min_coverage": 0.995,
            "clip_min_coverage": 0.993,
            "max_car_speed_kmh": 160.0,
        },
    )

    aggregate = summary["vehicle_speed_aggregate"]
    assert aggregate["dense_city_acceptance_min_coverage"] == 0.995
    assert aggregate["clip_acceptance_min_coverage"] == 0.993
    assert aggregate["clip_rows"][0]["passes_vehicle_speed_acceptance"] is True
    assert aggregate["passes_dense_city_acceptance"] is False


def test_run_regression_passes_speed_ground_truth_dir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clip_name = "063_dense_city_traffic_4k_elevated_0300s_30s.mp4"
    input_dir = tmp_path / "clips"
    input_dir.mkdir()
    (input_dir / clip_name).write_bytes(b"mp4")
    output_dir = tmp_path / "out"
    gt_dir = tmp_path / "gt"
    gt_dir.mkdir()
    regression_config = tmp_path / "vehicle_speed_regression.yaml"
    regression_config.write_text(
        yaml.safe_dump(
            {
                "default_set": "dense",
                "sets": {
                    "dense": {
                        "aggregate_min_coverage": 0.993,
                        "clip_min_coverage": 0.995,
                        "max_car_speed_kmh": 160.0,
                        "clips": [clip_name],
                    },
                },
            },
        ),
        encoding="utf-8",
    )
    captured: dict[str, Path | None] = {}

    def fake_analyze_clip(**kwargs):
        captured["speed_ground_truth_dir"] = kwargs.get("speed_ground_truth_dir")
        return {
            "clip": clip_name,
            "final_report": {
                "active_tracks": [
                    {
                        "class_id": 2,
                        "speed_kmh": 40.0,
                        "physics_valid": True,
                        "speed_confidence": 0.8,
                    },
                ],
                "regional_people_count": {"people_count": 0},
                "infrastructure_semantics": {"traffic_light_count": 0},
                "traffic_flow": {
                    "space_mean_speed_kmh": 40.0,
                    "flow_q_veh_per_hour": None,
                    "density_k_veh_per_km": None,
                    "congestion_level": "stable_flow",
                },
                "safety_metrics": {
                    "risk_level": "nominal",
                    "min_time_to_collision_sec": None,
                    "min_time_headway_sec": None,
                },
            },
            "scene_profile": {"name": "dense"},
            "calibration": {
                "source": "video_manual_preset",
                "quality": "good",
                "position_rmse_floor_m": 1.0,
                "scale_uncertainty_pct": 5.0,
            },
            "sensitivity": {"space_mean_speed_band_kmh": [39.0, 41.0]},
            "effective_processing_fps": 10.0,
            "vehicle_speed_audit": {
                "clip": clip_name,
                "vehicle_track_samples": 1,
                "displayable_vehicle_track_samples": 1,
                "vehicle_display_coverage": 1.0,
                "max_speed_by_class": {"car": 40.0},
            },
        }

    monkeypatch.setattr(run_vehicle_speed_regression, "analyze_clip", fake_analyze_clip)
    monkeypatch.setattr(
        run_vehicle_speed_regression,
        "load_calibration_presets",
        lambda _path: SimpleNamespace(scene_profiles={}, video_calibrations={}),
    )
    monkeypatch.setattr(run_vehicle_speed_regression, "load_camera_profiles", lambda _path: {})
    monkeypatch.setattr(run_vehicle_speed_regression, "resolve_device", lambda _device: "cpu")

    run_regression(
        argparse.Namespace(
            regression_config=str(regression_config),
            set=None,
            input_dir=str(input_dir),
            output_dir=str(output_dir),
            calibration_presets="unused.yaml",
            camera_profiles="unused.yaml",
            max_frames=1,
            frame_stride=1,
            confidence=0.35,
            model=None,
            device="cpu",
            clips=None,
            allow_empty=False,
            speed_ground_truth_dir=str(gt_dir),
        ),
    )

    assert captured["speed_ground_truth_dir"] == gt_dir
