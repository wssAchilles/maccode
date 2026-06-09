from __future__ import annotations

import csv
import json
from pathlib import Path

from scripts.generate_vehicle_speed_gt_samples import generate_vehicle_speed_gt_samples


def test_generate_vehicle_speed_gt_samples_writes_manual_template(tmp_path: Path) -> None:
    source = tmp_path / "results"
    source.mkdir()
    result_path = source / "063_dense_city.json"
    result_path.write_text(
        json.dumps(
            {
                "clip": "063_dense_city.mp4",
                "frame_reports": [
                    *[
                        {
                            "frame_index": frame_index,
                            "timestamp_sec": frame_index / 30.0,
                            "active_tracks": [
                                {
                                    "tracker_id": 1,
                                    "class_id": 2,
                                    "class_name": "car",
                                    "speed_kmh": 40.0 + frame_index * 0.01,
                                    "speed_uncertainty_kmh": 60.0,
                                    "speed_confidence": 0.05,
                                    "physics_valid": False,
                                    "speed_source": "fixed_lag_rts_backfill",
                                    "fixed_lag_backfilled": True,
                                    "quality_label": "low_confidence",
                                    "stability_label": "unstable_observation",
                                    "rejection_reason": "unstable_observation",
                                    "contact_fusion_confidence": 0.8,
                                },
                            ],
                        }
                        for frame_index in range(10, 16)
                    ],
                    {
                        "frame_index": 11,
                        "active_tracks": [
                            {
                                "tracker_id": 2,
                                "class_id": 2,
                                "class_name": "car",
                                "speed_kmh": 35.0,
                                "physics_valid": True,
                                "id_switch_risk": 0.9,
                            },
                        ],
                    },
                ],
            },
        ),
        encoding="utf-8",
    )
    output_csv = tmp_path / "manual_gt_samples.csv"

    summary = generate_vehicle_speed_gt_samples(
        [source],
        output_csv=output_csv,
        max_samples_per_clip=10,
    )

    rows = list(csv.DictReader(output_csv.open(encoding="utf-8")))
    reasons = {row["audit_reason"] for row in rows}

    assert summary["processed_clips"] == 1
    assert summary["sample_count"] == 2
    assert "rts_uncertainty_recalibrated" in reasons
    assert "hidden_id_switch_risk" in reasons
    assert rows[0]["gt_speed_kmh"] == ""
    assert (tmp_path / "manual_gt_samples.summary.json").exists()
