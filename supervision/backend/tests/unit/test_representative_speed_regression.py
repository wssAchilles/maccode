from __future__ import annotations

import argparse
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml
from scripts import run_representative_speed_regression
from scripts.run_representative_speed_regression import (
    available_clips,
    load_representative_set,
    run_regression,
    selected_clip_names,
)

REPRESENTATIVE_CLIPS = [
    "023_complex_signal_day_wide_0010s_30s.mp4",
    "029_red_light_static_0038s_30s.mp4",
    "033_pedestrian_crowd_high_view_0000s_30s.mp4",
    "042_pedestrian_crowd_high_view_0270s_30s.mp4",
]


def test_loads_representative_clip_selection_in_exact_order() -> None:
    regression = load_representative_set(
        Path("data/tests/representative_speed_regression.yaml"),
        None,
    )

    assert regression["name"] == "representative_fixed_camera_023_029_033_042"
    assert regression["clips"] == REPRESENTATIVE_CLIPS
    assert regression["clip_min_coverage"] == 0.995
    assert regression["pedestrian_clip_min_coverage"] == 0.995
    assert regression["target_speed_roles"] == {
        REPRESENTATIVE_CLIPS[0]: ["vehicle_speed"],
        REPRESENTATIVE_CLIPS[1]: ["vehicle_speed"],
        REPRESENTATIVE_CLIPS[2]: ["pedestrian_speed"],
        REPRESENTATIVE_CLIPS[3]: ["pedestrian_speed"],
    }


def test_available_clips_preserves_order_and_reports_missing(tmp_path: Path) -> None:
    (tmp_path / REPRESENTATIVE_CLIPS[1]).write_bytes(b"mp4")
    (tmp_path / REPRESENTATIVE_CLIPS[0]).write_bytes(b"mp4")

    selected, missing = available_clips(tmp_path, REPRESENTATIVE_CLIPS[:3])

    assert [path.name for path in selected] == REPRESENTATIVE_CLIPS[:2]
    assert missing == [REPRESENTATIVE_CLIPS[2]]


def test_selected_clip_names_rejects_outside_representative_set() -> None:
    with pytest.raises(ValueError, match="not in the representative speed regression set"):
        selected_clip_names(REPRESENTATIVE_CLIPS, ["063_dense_city.mp4"])


def test_run_regression_writes_combined_vehicle_and_pedestrian_benchmark(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    input_dir = tmp_path / "clips"
    input_dir.mkdir()
    selected_clips = [REPRESENTATIVE_CLIPS[0], REPRESENTATIVE_CLIPS[2]]
    for clip in selected_clips:
        (input_dir / clip).write_bytes(b"mp4")
    output_dir = tmp_path / "out"
    regression_config = tmp_path / "representative_speed_regression.yaml"
    regression_config.write_text(
        yaml.safe_dump(
            {
                "default_set": "representative",
                "sets": {
                    "representative": {
                        "aggregate_min_coverage": 0.995,
                        "clip_min_coverage": 0.995,
                        "pedestrian_clip_min_coverage": 0.995,
                        "max_car_speed_kmh": 160.0,
                        "pedestrian_max_speed_kmh": 18.0,
                        "target_speed_roles": {
                            REPRESENTATIVE_CLIPS[0]: ["vehicle_speed"],
                            REPRESENTATIVE_CLIPS[2]: ["pedestrian_speed"],
                        },
                        "clips": selected_clips,
                    },
                },
            },
        ),
        encoding="utf-8",
    )

    def fake_analyze_clip(**kwargs):
        clip = Path(kwargs["path"]).name
        if clip.startswith("023_"):
            pedestrian_tracks = [
                {
                    "class_id": 0,
                    "class_name": "person",
                    "tracker_id": 17,
                    "speed_kmh": 4.2,
                    "physics_valid": True,
                    "speed_confidence": 0.9,
                    "speed_uncertainty_kmh": 20.0,
                },
            ]
            return {
                "clip": clip,
                "final_report": _final_report(pedestrian_tracks),
                "frame_reports": [
                    _vehicle_report(
                        clip,
                        displayable=994,
                        samples=1000,
                        active_tracks=pedestrian_tracks,
                    ),
                ],
                "scene_profile": {"name": "wide_signalized_intersection"},
                "calibration": _calibration(),
                "sensitivity": {"space_mean_speed_band_kmh": [39.0, 41.0]},
                "effective_processing_fps": 10.0,
                "vehicle_speed_audit": {
                    "clip": clip,
                    "vehicle_track_samples": 1000,
                    "displayable_vehicle_track_samples": 994,
                    "vehicle_display_coverage": 0.994,
                    "safe_vehicle_track_samples": 1000,
                    "safe_displayable_vehicle_track_samples": 1000,
                    "safe_vehicle_display_coverage": 1.0,
                    "max_speed_by_class": {"car": 40.0},
                },
            }
        pedestrian_tracks = [
            {
                "class_id": 0,
                "class_name": "person",
                "tracker_id": 7,
                "speed_kmh": 4.2,
                "physics_valid": True,
                "speed_confidence": 0.9,
                "speed_uncertainty_kmh": 1.0,
            },
        ]
        return {
            "clip": clip,
            "final_report": _final_report(pedestrian_tracks),
            "frame_reports": [{"frame_index": 1, "active_tracks": pedestrian_tracks}],
            "scene_profile": {"name": "pedestrian_high_view"},
            "calibration": _calibration(),
            "sensitivity": {"space_mean_speed_band_kmh": [None, None]},
            "effective_processing_fps": 10.0,
            "vehicle_speed_audit": {
                "clip": clip,
                "vehicle_track_samples": 0,
                "displayable_vehicle_track_samples": 0,
                "vehicle_display_coverage": None,
                "max_speed_by_class": {},
            },
        }

    monkeypatch.setattr(run_representative_speed_regression, "analyze_clip", fake_analyze_clip)
    monkeypatch.setattr(
        run_representative_speed_regression,
        "load_calibration_presets",
        lambda _path: SimpleNamespace(scene_profiles={}, video_calibrations={}),
    )
    monkeypatch.setattr(
        run_representative_speed_regression,
        "load_camera_profiles",
        lambda _path: {},
    )
    monkeypatch.setattr(run_representative_speed_regression, "resolve_device", lambda _: "cpu")

    payload = run_regression(
        argparse.Namespace(
            regression_config=str(regression_config),
            set=None,
            input_dir=str(input_dir),
            output_dir=str(output_dir),
            calibration_presets="unused.yaml",
            camera_profiles="unused.yaml",
            max_frames=1,
            frame_stride=1,
            confidence=0.45,
            model=None,
            device="cpu",
            clips=None,
            allow_empty=False,
            speed_ground_truth_dir=str(tmp_path / "gt"),
        ),
    )

    benchmark = payload["representative_speed_benchmark"]
    vehicle_row = benchmark["vehicle_clip_rows_evaluated"][0]
    assert benchmark["target_vehicle_clips"] == [REPRESENTATIVE_CLIPS[0]]
    assert benchmark["target_pedestrian_clips"] == [REPRESENTATIVE_CLIPS[2]]
    assert [row["clip"] for row in benchmark["vehicle_clip_rows_evaluated"]] == [
        REPRESENTATIVE_CLIPS[0],
    ]
    assert [row["clip"] for row in benchmark["pedestrian_clip_rows_evaluated"]] == [
        REPRESENTATIVE_CLIPS[2],
    ]
    assert vehicle_row["coverage_used_for_acceptance"] == 0.994
    assert vehicle_row["passes_vehicle_speed_acceptance"] is False
    assert benchmark["pedestrian_speed_aggregate"]["pedestrian_display_coverage"] == 1.0
    assert benchmark["passes_representative_speed_acceptance"] is False
    assert (output_dir / "benchmark_summary.json").exists()
    assert (output_dir / "benchmark_report.md").exists()


def _vehicle_report(
    clip: str,
    *,
    displayable: int,
    samples: int,
    active_tracks: list[dict] | None = None,
) -> dict:
    return {
        "frame_index": 1,
        "active_tracks": active_tracks or [],
        "clip": clip,
        "vehicle_speed_audit": {
            "vehicle_track_samples": samples,
            "displayable_vehicle_track_samples": displayable,
        },
    }


def _final_report(active_tracks: list[dict]) -> dict:
    return {
        "active_tracks": active_tracks,
        "regional_people_count": {"people_count": 0},
        "infrastructure_semantics": {"traffic_light_count": 0, "static_context": []},
        "traffic_flow": {
            "space_mean_speed_kmh": None,
            "flow_q_veh_per_hour": None,
            "density_k_veh_per_km": None,
            "congestion_level": "stable_flow",
        },
        "safety_metrics": {
            "risk_level": "nominal",
            "min_time_to_collision_sec": None,
            "min_time_headway_sec": None,
        },
    }


def _calibration() -> dict:
    return {
        "source": "video_manual_preset",
        "quality": "good",
        "position_rmse_floor_m": 1.0,
        "scale_uncertainty_pct": 5.0,
    }
