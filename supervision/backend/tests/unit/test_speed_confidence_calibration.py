from __future__ import annotations

from typing import cast

from domain.speed.confidence_calibration import SpeedConfidenceCalibrator


def test_confidence_calibrator_degrades_unstable_proxy_observation() -> None:
    clean = {
        "speed_confidence": 0.9,
        "bev_risk_level": "trusted",
        "contact_fusion_confidence": 0.9,
        "speed_uncertainty_kmh": 3.0,
    }
    unstable = {
        **clean,
        "bev_risk_level": "rejected",
        "speed_uncertainty_kmh": 35.0,
        "id_switch_risk": 0.9,
        "jerk_p95_mps3": 20.0,
    }

    calibrator = SpeedConfidenceCalibrator()
    clean_result = calibrator.calibrate(clean)
    unstable_result = calibrator.calibrate(unstable)

    assert clean_result.confidence > unstable_result.confidence
    assert unstable_result.proxy_low_confidence is True
    assert unstable_result.bin_label in {"very_low", "low"}


def test_confidence_calibration_summary_counts_bins() -> None:
    reports = [
        {
            "active_tracks": [
                {"speed_kmh": 30.0, "speed_confidence": 0.8},
                {"speed_kmh": 40.0, "speed_confidence": 0.2, "speed_frozen": True},
            ]
        }
    ]

    summary = SpeedConfidenceCalibrator().summarize(reports)

    assert summary["speed_track_count"] == 2
    assert cast(int, summary["proxy_low_confidence_count"]) >= 1
    assert isinstance(summary["confidence_bins"], dict)
