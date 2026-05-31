from __future__ import annotations

import json
from pathlib import Path

import yaml
from scripts.import_golden_calibration_picks import import_picks


def test_import_picks_writes_video_manual_preset_and_runs_gate(tmp_path: Path) -> None:
    picks_path = tmp_path / "picks.json"
    profile_path = tmp_path / "profiles.yaml"
    presets_path = tmp_path / "calibration_presets.yaml"
    clip = "026_complex_signal_day_wide_0115s_30s.mp4"
    picks_path.write_text(
        json.dumps(
            {
                clip: {
                    "annotation_method": "manual_ground_control_point_picker",
                    "annotation_confidence": 0.82,
                    "evidence_sources": [
                        "manual_pixel_point_collection",
                        "surveyed_lane_width_anchor",
                    ],
                    "auto_geometry": {
                        "candidate_line_count": 3,
                        "longitudinal_count": 2,
                        "lateral_count": 1,
                    },
                    "scale_constraints": [
                        {
                            "name": "lane_width",
                            "kind": "traffic_engineering_prior",
                            "nominal_m": 3.5,
                        },
                    ],
                    "scale_prior": {
                        "kind": "surveyed_lane_width",
                        "description": "surveyed 20m road width",
                    },
                    "road_plane_polygon_pixel": [
                        [100, 600],
                        [500, 600],
                        [450, 300],
                        [150, 300],
                    ],
                    "road_plane_polygon_world": [
                        [0, 0],
                        [20, 0],
                        [20, 60],
                        [0, 60],
                    ],
                    "control_points": [
                        {"pixel": [100, 600], "world": [0, 0]},
                        {"pixel": [500, 600], "world": [20, 0]},
                        {"pixel": [450, 300], "world": [20, 60]},
                        {"pixel": [150, 300], "world": [0, 60]},
                        {"pixel": [300, 600], "world": [10, 0]},
                        {"pixel": [300, 300], "world": [10, 60]},
                        {"pixel": [205.26315789, 536.84210526], "world": [5, 10]},
                        {"pixel": [394.73684211, 536.84210526], "world": [15, 10]},
                    ],
                    "validation_segments": [
                        {
                            "pixel_start": [214.28571429, 428.57142857],
                            "pixel_end": [385.71428571, 428.57142857],
                            "world_start": [5, 30],
                            "world_end": [15, 30],
                        },
                        {
                            "pixel_start": [210, 480],
                            "pixel_end": [390, 480],
                            "world_start": [5, 20],
                            "world_end": [15, 20],
                        },
                    ],
                },
            },
        ),
        encoding="utf-8",
    )
    profile_path.write_text(
        yaml.safe_dump(
            {
                clip: {
                    "world_width_m": 20,
                    "world_length_m": 60,
                    "scale_prior_description": "surveyed 20m road width",
                    "profile_notes": "fixed camera, flat road plane",
                    "position_rmse_floor_m": 0.4,
                    "calibration_scale_uncertainty_pct": 3.0,
                },
            },
        ),
        encoding="utf-8",
    )

    result = import_picks(
        picks_path,
        profile_path,
        presets_path,
        clips=[clip],
        trusted=True,
    )

    assert result["trusted_count"] == 1
    saved = yaml.safe_load(presets_path.read_text(encoding="utf-8"))
    entry = saved["video_calibrations"][clip]
    assert entry["calibration_trusted"] is True
    assert entry["scale_prior"]["kind"] == "surveyed_lane_width"
    assert entry["scale_prior"]["description"] == "surveyed 20m road width"
    assert entry["annotation_method"] == "manual_ground_control_point_picker"
    assert entry["annotation_confidence"] == 0.82
    assert entry["evidence_sources"] == [
        "manual_pixel_point_collection",
        "surveyed_lane_width_anchor",
    ]
    assert entry["auto_geometry"]["candidate_line_count"] == 3
    assert entry["scale_constraints"][0]["nominal_m"] == 3.5
    assert len(entry["points"]) == 8
    assert len(entry["validation_segments"]) == 2
    assert entry["road_plane_polygon_pixel"] == [
        [100.0, 600.0],
        [500.0, 600.0],
        [450.0, 300.0],
        [150.0, 300.0],
    ]


def test_import_picks_can_read_profile_metadata_from_picker_json(tmp_path: Path) -> None:
    picks_path = tmp_path / "picks.json"
    presets_path = tmp_path / "calibration_presets.yaml"
    clip = "026_complex_signal_day_wide_0115s_30s.mp4"
    picks_path.write_text(
        json.dumps(
            {
                clip: {
                    "polygon": [[100, 600], [500, 600], [450, 300], [150, 300]],
                    "points": [
                        {"pixel": [100, 600], "world": [0, 0]},
                        {"pixel": [500, 600], "world": [20, 0]},
                        {"pixel": [450, 300], "world": [20, 60]},
                        {"pixel": [150, 300], "world": [0, 60]},
                        {"pixel": [300, 600], "world": [10, 0]},
                        {"pixel": [300, 300], "world": [10, 60]},
                        {"pixel": [205.26315789, 536.84210526], "world": [5, 10]},
                        {"pixel": [394.73684211, 536.84210526], "world": [15, 10]},
                    ],
                    "segments": [
                        {
                            "pixel_start": [214.28571429, 428.57142857],
                            "pixel_end": [385.71428571, 428.57142857],
                            "world_start": [5, 30],
                            "world_end": [15, 30],
                        },
                        {
                            "pixel_start": [210, 480],
                            "pixel_end": [390, 480],
                            "world_start": [5, 20],
                            "world_end": [15, 20],
                        },
                    ],
                },
                "__profile_metadata__": {
                    clip: {
                        "world_width_m": 20,
                        "world_length_m": 60,
                        "scale_prior_description": "surveyed 20m road width",
                        "profile_notes": "fixed camera, flat road plane",
                    },
                },
            },
        ),
        encoding="utf-8",
    )

    result = import_picks(
        picks_path,
        None,
        presets_path,
        clips=[clip],
        trusted=True,
    )

    assert result["profile_metadata_path"] == "embedded:__profile_metadata__"
    assert result["trusted_count"] == 1


def test_import_picks_downgrades_visual_prior_even_with_low_rmse(
    tmp_path: Path,
) -> None:
    picks_path = tmp_path / "picks.json"
    profile_path = tmp_path / "profiles.yaml"
    presets_path = tmp_path / "calibration_presets.yaml"
    clip = "026_complex_signal_day_wide_0115s_30s.mp4"
    picks_path.write_text(
        json.dumps(
            {
                clip: {
                    "annotation_method": "agent_cv_geometry_prior_homography",
                    "evidence_sources": ["opencv_canny_hough_line_candidates"],
                    "scale_prior": {
                        "kind": "traffic_standard_visual_prior",
                        "description": "visual-prior, not a field survey",
                    },
                    "polygon": [[100, 600], [500, 600], [450, 300], [150, 300]],
                    "points": [
                        {"pixel": [100, 600], "world": [0, 0]},
                        {"pixel": [500, 600], "world": [20, 0]},
                        {"pixel": [450, 300], "world": [20, 60]},
                        {"pixel": [150, 300], "world": [0, 60]},
                        {"pixel": [300, 600], "world": [10, 0]},
                        {"pixel": [300, 300], "world": [10, 60]},
                        {"pixel": [205.26315789, 536.84210526], "world": [5, 10]},
                        {"pixel": [394.73684211, 536.84210526], "world": [15, 10]},
                    ],
                    "segments": [
                        {
                            "pixel_start": [214.28571429, 428.57142857],
                            "pixel_end": [385.71428571, 428.57142857],
                            "world_start": [5, 30],
                            "world_end": [15, 30],
                        },
                        {
                            "pixel_start": [210, 480],
                            "pixel_end": [390, 480],
                            "world_start": [5, 20],
                            "world_end": [15, 20],
                        },
                    ],
                },
            },
        ),
        encoding="utf-8",
    )
    profile_path.write_text(
        yaml.safe_dump(
            {
                clip: {
                    "world_width_m": 20,
                    "world_length_m": 60,
                    "scale_prior_description": "surveyed 20m road width",
                    "profile_notes": "fixed camera, flat road plane",
                },
            },
        ),
        encoding="utf-8",
    )

    result = import_picks(
        picks_path,
        profile_path,
        presets_path,
        clips=[clip],
        trusted=True,
    )

    assert result["trusted_count"] == 0
    saved = yaml.safe_load(presets_path.read_text(encoding="utf-8"))
    assert saved["video_calibrations"][clip]["calibration_trusted"] is False


def test_import_picks_requires_profile_metadata(tmp_path: Path) -> None:
    picks_path = tmp_path / "picks.json"
    profile_path = tmp_path / "profiles.yaml"
    clip = "026_complex_signal_day_wide_0115s_30s.mp4"
    picks_path.write_text(json.dumps({clip: {"points": []}}), encoding="utf-8")
    profile_path.write_text("{}", encoding="utf-8")

    try:
        import_picks(picks_path, profile_path, tmp_path / "calibration.yaml", clips=[clip])
    except ValueError as exc:
        assert "missing profile metadata" in str(exc)
    else:
        raise AssertionError("missing profile metadata should fail")


def test_import_picks_rejects_placeholder_scale_prior(tmp_path: Path) -> None:
    picks_path = tmp_path / "picks.json"
    profile_path = tmp_path / "profiles.yaml"
    clip = "026_complex_signal_day_wide_0115s_30s.mp4"
    picks_path.write_text(
        json.dumps({clip: {"points": [], "segments": [], "polygon": []}}),
        encoding="utf-8",
    )
    profile_path.write_text(
        yaml.safe_dump(
            {
                clip: {
                    "world_width_m": 20,
                    "world_length_m": 60,
                    "scale_prior_description": "REPLACE_WITH_REAL_SCALE_PRIOR",
                    "profile_notes": "fixed camera",
                },
            },
        ),
        encoding="utf-8",
    )

    try:
        import_picks(picks_path, profile_path, tmp_path / "calibration.yaml", clips=[clip])
    except ValueError as exc:
        assert "scale_prior_description" in str(exc)
    else:
        raise AssertionError("placeholder scale prior should fail")


def test_import_picks_rejects_trusted_import_without_full_evidence(tmp_path: Path) -> None:
    picks_path = tmp_path / "picks.json"
    profile_path = tmp_path / "profiles.yaml"
    clip = "026_complex_signal_day_wide_0115s_30s.mp4"
    picks_path.write_text(
        json.dumps(
            {
                clip: {
                    "points": [
                        {"pixel": [100, 600], "world": [0, 0]},
                        {"pixel": [500, 600], "world": [20, 0]},
                        {"pixel": [450, 300], "world": [20, 60]},
                        {"pixel": [150, 300], "world": [0, 60]},
                    ],
                    "segments": [],
                    "polygon": [],
                },
            },
        ),
        encoding="utf-8",
    )
    profile_path.write_text(
        yaml.safe_dump(
            {
                clip: {
                    "world_width_m": 20,
                    "world_length_m": 60,
                    "scale_prior_description": "surveyed road width",
                    "profile_notes": "fixed camera, flat road plane",
                },
            },
        ),
        encoding="utf-8",
    )

    try:
        import_picks(
            picks_path,
            profile_path,
            tmp_path / "calibration.yaml",
            clips=[clip],
            trusted=True,
        )
    except ValueError as exc:
        message = str(exc)
        assert "cannot be imported as trusted" in message
        assert "at least 8 manual control points" in message
        assert "road_plane_polygon_pixel" in message
    else:
        raise AssertionError("trusted import without full evidence should fail")
