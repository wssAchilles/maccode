from __future__ import annotations

import json
from pathlib import Path

from scripts.merge_golden_calibration_picks import merge_pick_payloads


def test_merge_pick_payloads_combines_clips_and_metadata(tmp_path: Path) -> None:
    first = tmp_path / "026.json"
    second = tmp_path / "042.json"
    first.write_text(
        json.dumps(
            {
                "026_complex_signal_day_wide_0115s_30s.mp4": {
                    "points": [],
                    "segments": [],
                    "polygon": [],
                },
                "__profile_metadata__": {
                    "026_complex_signal_day_wide_0115s_30s.mp4": {
                        "world_width_m": 28,
                    },
                },
            },
        ),
        encoding="utf-8",
    )
    second.write_text(
        json.dumps(
            {
                "042_pedestrian_crowd_high_view_0270s_30s.mp4": {
                    "points": [],
                    "segments": [],
                    "polygon": [],
                },
                "__profile_metadata__": {
                    "042_pedestrian_crowd_high_view_0270s_30s.mp4": {
                        "world_width_m": 22,
                    },
                },
            },
        ),
        encoding="utf-8",
    )

    merged = merge_pick_payloads([first, second])

    assert sorted(key for key in merged if not key.startswith("__")) == [
        "026_complex_signal_day_wide_0115s_30s.mp4",
        "042_pedestrian_crowd_high_view_0270s_30s.mp4",
    ]
    assert merged["__profile_metadata__"][
        "026_complex_signal_day_wide_0115s_30s.mp4"
    ]["world_width_m"] == 28


def test_merge_pick_payloads_rejects_duplicate_clip(tmp_path: Path) -> None:
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    clip = "026_complex_signal_day_wide_0115s_30s.mp4"
    first.write_text(json.dumps({clip: {"points": []}}), encoding="utf-8")
    second.write_text(json.dumps({clip: {"points": []}}), encoding="utf-8")

    try:
        merge_pick_payloads([first, second])
    except ValueError as exc:
        assert "duplicate clip entries" in str(exc)
    else:
        raise AssertionError("duplicate clip entries should fail")
