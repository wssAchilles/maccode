from __future__ import annotations

from pathlib import Path

import pytest
from scripts.run_vehicle_speed_regression import (
    available_clips,
    load_regression_set,
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
