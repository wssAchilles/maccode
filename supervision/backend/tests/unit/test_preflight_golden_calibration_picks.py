from __future__ import annotations

import json
from pathlib import Path

import yaml
from scripts.preflight_golden_calibration_picks import preflight_picks, render_markdown


def write_valid_pick_files(tmp_path: Path, clip: str) -> tuple[Path, Path]:
    picks_path = tmp_path / "picks.json"
    profile_path = tmp_path / "profiles.yaml"
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
    return picks_path, profile_path


def test_preflight_picks_reports_ready_clip(tmp_path: Path) -> None:
    clip = "026_complex_signal_day_wide_0115s_30s.mp4"
    picks_path, profile_path = write_valid_pick_files(tmp_path, clip)

    result = preflight_picks(
        picks_path=picks_path,
        profile_metadata_path=profile_path,
        clips=[clip],
    )

    assert result["all_ready"] is True
    assert result["ready_count"] == 1
    assert result["clips"][0]["point_count"] == 8
    assert result["clips"][0]["calibration_trusted"] is True
    assert "Ready clips" in render_markdown(result)


def test_preflight_picks_reads_embedded_profile_metadata(tmp_path: Path) -> None:
    clip = "026_complex_signal_day_wide_0115s_30s.mp4"
    picks_path, profile_path = write_valid_pick_files(tmp_path, clip)
    picks = json.loads(picks_path.read_text(encoding="utf-8"))
    profiles = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    picks["__profile_metadata__"] = profiles
    picks_path.write_text(json.dumps(picks), encoding="utf-8")

    result = preflight_picks(
        picks_path=picks_path,
        profile_metadata_path=None,
        clips=[clip],
    )

    assert result["all_ready"] is True
    assert result["profile_metadata_path"] == "embedded:__profile_metadata__"


def test_preflight_picks_surfaces_visual_prior_provenance_issue(
    tmp_path: Path,
) -> None:
    clip = "026_complex_signal_day_wide_0115s_30s.mp4"
    picks_path, profile_path = write_valid_pick_files(tmp_path, clip)
    picks = json.loads(picks_path.read_text(encoding="utf-8"))
    picks[clip]["annotation_method"] = "agent_cv_geometry_prior_homography"
    picks[clip]["evidence_sources"] = ["opencv_canny_hough_line_candidates"]
    picks[clip]["scale_prior"] = {
        "kind": "traffic_standard_visual_prior",
        "description": "visual-prior, not a field survey",
    }
    picks_path.write_text(json.dumps(picks), encoding="utf-8")

    result = preflight_picks(
        picks_path=picks_path,
        profile_metadata_path=profile_path,
        clips=[clip],
    )

    row = result["clips"][0]
    assert row["preflight_ready"] is False
    assert row["provenance_trusted"] is False
    assert any("annotation_method" in issue for issue in row["issues"])


def test_preflight_picks_reports_missing_evidence(tmp_path: Path) -> None:
    picks_path = tmp_path / "missing.json"
    profile_path = tmp_path / "profiles.yaml"
    clip = "026_complex_signal_day_wide_0115s_30s.mp4"
    picks_path.write_text("{}", encoding="utf-8")
    profile_path.write_text("{}", encoding="utf-8")

    result = preflight_picks(
        picks_path=picks_path,
        profile_metadata_path=profile_path,
        clips=[clip],
    )

    assert result["all_ready"] is False
    assert result["ready_count"] == 0
    assert result["clips"][0]["issues"] == [
        "missing picks",
        "missing profile metadata",
    ]


def test_preflight_picks_reports_missing_files(tmp_path: Path) -> None:
    clip = "026_complex_signal_day_wide_0115s_30s.mp4"

    result = preflight_picks(
        picks_path=tmp_path / "missing-picks.json",
        profile_metadata_path=tmp_path / "missing-profiles.yaml",
        clips=[clip],
    )

    assert result["all_ready"] is False
    assert result["file_issues"] == [
        f"missing picks file: {tmp_path / 'missing-picks.json'}",
        f"missing profile metadata file: {tmp_path / 'missing-profiles.yaml'}",
    ]
    markdown = render_markdown(result)
    assert "## File Issues" in markdown
