from __future__ import annotations

from scripts.validate_pedestrian_speed_training import validate_summary


def test_validate_training_summary_passes_acceptance_gates() -> None:
    failures = validate_summary(
        {
            "aggregate": {
                "train": {"person_speed_coverage": 0.999},
                "validation": {"person_speed_coverage": 0.996},
            },
            "by_clip": {
                "033_pedestrian_crowd_high_view_0000s_30s.mp4": {
                    "person_speed_coverage": 1.0,
                    "max_pedestrian_speed_kmh": 17.9,
                },
                "040_pedestrian_crowd_high_view_0210s_30s.mp4": {
                    "person_speed_coverage": 0.996,
                    "max_pedestrian_speed_kmh": 12.0,
                },
            },
        },
        train_coverage_min=0.998,
        validation_coverage_min=0.995,
        max_person_speed_kmh=18.0,
        clip_033_coverage_min=1.0,
    )

    assert failures == []


def test_validate_training_summary_reports_gate_failures() -> None:
    failures = validate_summary(
        {
            "aggregate": {
                "train": {"person_speed_coverage": 0.9},
                "validation": {"person_speed_coverage": 0.8},
            },
            "by_clip": {
                "033_pedestrian_crowd_high_view_0000s_30s.mp4": {
                    "person_speed_coverage": 0.99,
                    "max_pedestrian_speed_kmh": 19.0,
                },
            },
        },
        train_coverage_min=0.998,
        validation_coverage_min=0.995,
        max_person_speed_kmh=18.0,
        clip_033_coverage_min=1.0,
    )

    assert len(failures) == 4


def test_validate_training_summary_reports_baseline_regressions() -> None:
    failures = validate_summary(
        {
            "aggregate": {
                "train": {"person_speed_coverage": 0.999},
                "validation": {"person_speed_coverage": 0.996},
            },
            "by_clip": {
                "033_pedestrian_crowd_high_view_0000s_30s.mp4": {
                    "person_speed_coverage": 1.0,
                    "max_pedestrian_speed_kmh": 17.9,
                },
            },
            "speed_jump_baseline_comparison": {
                "aggregate": {
                    "validation": {"speed_jump_p95_not_increased": False},
                },
            },
            "model_evaluation": {
                "contact_quality_model": {
                    "baseline": {"calibration_improved": False},
                },
            },
            "manual_audit_proxy": {
                "validation": {
                    "obvious_error_candidate_ratio": 0.03,
                    "acceptance_max_ratio": 0.02,
                },
            },
        },
        train_coverage_min=0.998,
        validation_coverage_min=0.995,
        max_person_speed_kmh=18.0,
        clip_033_coverage_min=1.0,
    )

    assert "validation speed jump p95 increased above baseline" in failures
    assert "contact quality model did not improve validation calibration" in failures
    assert "validation obvious error candidate ratio 0.0300 exceeds 0.0200" in failures
