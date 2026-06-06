from __future__ import annotations

import json

from scripts.summarize_model_comparison_benchmark import summarize


def test_model_comparison_summary_reads_phase3_diagnostics(tmp_path) -> None:  # type: ignore[no-untyped-def]
    payload = {
        "final_report": {
            "model_comparison_benchmark": {
                "baseline": {"speed_jump_p95_kmh": 10.0},
                "optimized": {"speed_jump_p95_kmh": 8.0},
                "gates": {"speed_jump_p95_not_increased": True},
            },
            "confidence_calibration_summary": {
                "proxy_low_confidence_ratio": 0.25,
            },
            "tracklet_reassociation_summary": {
                "relinked_count": 2,
            },
            "calibration_sensitivity": {
                "speed_sensitivity_p95": 0.08,
            },
        }
    }
    (tmp_path / "clip.json").write_text(json.dumps(payload))

    summary = summarize(tmp_path)

    assert summary["clip_count"] == 1
    row = summary["rows"][0]
    assert row["proxy_low_confidence_ratio"] == 0.25
    assert row["tracklet_relinked_count"] == 2
    assert row["speed_sensitivity_p95"] == 0.08
