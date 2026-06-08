from __future__ import annotations

from domain.speed.vehicle_diagnostics import (
    VEHICLE_SPEED_REPORT_SCHEMA_VERSION,
    annotate_vehicle_speed_reports,
    build_vehicle_speed_aggregate,
    build_vehicle_speed_audit,
    processed_video_needs_regeneration,
    write_vehicle_speed_audit,
)


def test_vehicle_speed_reports_mark_reconstruction_and_freeze_last_valid_speed() -> None:
    reports = [
        {
            "frame_index": 1,
            "active_tracks": [
                {
                    "tracker_id": 7,
                    "class_id": 2,
                    "class_name": "car",
                    "speed_kmh": 36.0,
                    "speed_uncertainty_kmh": 3.0,
                    "speed_confidence": 0.8,
                    "physics_valid": True,
                    "quality_label": "stable",
                },
            ],
        },
        {
            "frame_index": 2,
            "active_tracks": [
                {
                    "tracker_id": 7,
                    "class_id": 2,
                    "class_name": "car",
                    "speed_kmh": None,
                    "physics_valid": False,
                    "quality_label": "low_confidence",
                    "track_age_frames": 10,
                },
            ],
        },
    ]

    updated = annotate_vehicle_speed_reports(
        reports,
        reconstruction_applied=True,
        source_commit_value="abc123",
    )
    frozen_track = updated[1]["active_tracks"][0]
    audit = build_vehicle_speed_audit(updated, clip="063_dense_city.mp4")

    assert updated[0]["report_schema_version"] == VEHICLE_SPEED_REPORT_SCHEMA_VERSION
    assert updated[0]["reconstruction_applied"] is True
    assert updated[0]["source_commit"] == "abc123"
    assert frozen_track["speed_kmh"] == 36.0
    assert frozen_track["physics_valid"] is True
    assert frozen_track["speed_source"] == "frozen_last_valid"
    assert frozen_track["vehicle_speed_display_state"] == "frozen_last_valid"
    assert audit["vehicle_display_coverage"] == 1.0
    assert audit["frozen_last_valid_count"] == 1


def test_vehicle_speed_reports_backfill_vehicle_warmup_from_next_valid_speed() -> None:
    reports = [
        {
            "frame_index": 1,
            "active_tracks": [
                {
                    "tracker_id": 7,
                    "class_id": 2,
                    "class_name": "car",
                    "speed_kmh": None,
                    "physics_valid": False,
                    "quality_label": "warming_up",
                    "stability_label": "insufficient_samples",
                    "track_age_frames": 1,
                    "id_switch_risk": 0.0,
                },
            ],
        },
        {
            "frame_index": 3,
            "active_tracks": [
                {
                    "tracker_id": 7,
                    "class_id": 2,
                    "class_name": "car",
                    "speed_kmh": 31.0,
                    "speed_uncertainty_kmh": 4.0,
                    "speed_confidence": 0.82,
                    "physics_valid": True,
                    "quality_label": "stable",
                    "track_age_frames": 3,
                },
            ],
        },
    ]

    updated = annotate_vehicle_speed_reports(
        reports,
        reconstruction_applied=True,
        source_commit_value="abc123",
    )
    warmup_track = updated[0]["active_tracks"][0]
    audit = build_vehicle_speed_audit(updated)

    assert warmup_track["speed_kmh"] == 31.0
    assert warmup_track["physics_valid"] is True
    assert warmup_track["speed_source"] == "fixed_lag_warmup_backfill"
    assert warmup_track["fixed_lag_backfilled"] is True
    assert warmup_track["vehicle_speed_display_state"] == "fixed_lag_refined"
    assert warmup_track["vehicle_speed_warmup_backfilled"] is True
    assert audit["vehicle_display_coverage"] == 1.0


def test_vehicle_speed_reports_do_not_freeze_hard_rejected_speed() -> None:
    reports = [
        {
            "frame_index": 1,
            "active_tracks": [
                {
                    "tracker_id": 8,
                    "class_id": 2,
                    "class_name": "car",
                    "speed_kmh": 50.0,
                    "physics_valid": True,
                    "quality_label": "stable",
                },
            ],
        },
        {
            "frame_index": 2,
            "active_tracks": [
                {
                    "tracker_id": 8,
                    "class_id": 2,
                    "class_name": "car",
                    "speed_kmh": None,
                    "physics_valid": False,
                    "quality_label": "rejected",
                    "rejection_reason": "class_speed_limit",
                    "track_age_frames": 10,
                },
            ],
        },
    ]

    updated = annotate_vehicle_speed_reports(reports, reconstruction_applied=True)
    rejected_track = updated[1]["active_tracks"][0]
    audit = build_vehicle_speed_audit(updated)

    assert rejected_track["speed_kmh"] is None
    assert rejected_track["physics_valid"] is False
    assert rejected_track["vehicle_speed_display_state"] == "rejected_hidden"
    assert rejected_track["speed_display_hidden"] is True
    assert audit["vehicle_display_coverage"] == 0.5
    assert audit["na_by_reason"] == {"rejected_hidden": 1}


def test_vehicle_speed_reports_admit_safe_fixed_lag_reconstructed_speed() -> None:
    reports = [
        {
            "frame_index": 10,
            "active_tracks": [
                {
                    "tracker_id": 33,
                    "class_id": 2,
                    "class_name": "car",
                    "speed_kmh": 42.5,
                    "speed_uncertainty_kmh": 18.0,
                    "speed_confidence": 0.12,
                    "physics_valid": False,
                    "quality_label": "low_confidence",
                    "stability_label": "unstable_observation",
                    "rejection_reason": "unstable_observation",
                    "speed_source": "fixed_lag_rts_backfill",
                    "fixed_lag_backfilled": True,
                    "id_switch_risk": 0.1,
                },
            ],
        },
    ]

    updated = annotate_vehicle_speed_reports(reports, reconstruction_applied=True)
    recovered_track = updated[0]["active_tracks"][0]
    audit = build_vehicle_speed_audit(updated)

    assert recovered_track["physics_valid"] is True
    assert recovered_track["vehicle_speed_display_state"] == "fixed_lag_refined"
    assert recovered_track["vehicle_speed_recovered_from_unstable_observation"] is True
    assert recovered_track["speed_display_hidden"] is False
    assert audit["vehicle_display_coverage"] == 1.0


def test_vehicle_speed_reports_do_not_admit_fixed_lag_speed_with_id_switch_risk() -> None:
    reports = [
        {
            "frame_index": 10,
            "active_tracks": [
                {
                    "tracker_id": 33,
                    "class_id": 2,
                    "class_name": "car",
                    "speed_kmh": 42.5,
                    "speed_uncertainty_kmh": 18.0,
                    "physics_valid": False,
                    "quality_label": "low_confidence",
                    "stability_label": "unstable_observation",
                    "rejection_reason": "unstable_observation",
                    "speed_source": "fixed_lag_rts_backfill",
                    "fixed_lag_backfilled": True,
                    "id_switch_risk": 0.9,
                    "track_age_frames": 10,
                },
            ],
        },
    ]

    updated = annotate_vehicle_speed_reports(reports, reconstruction_applied=True)
    rejected_track = updated[0]["active_tracks"][0]

    assert rejected_track["physics_valid"] is False
    assert rejected_track["vehicle_speed_display_state"] == "rejected_hidden"
    assert rejected_track["speed_display_hidden"] is True


def test_vehicle_speed_reports_do_not_admit_fixed_lag_speed_over_hard_limit() -> None:
    reports = [
        {
            "frame_index": 10,
            "active_tracks": [
                {
                    "tracker_id": 33,
                    "class_id": 2,
                    "class_name": "car",
                    "speed_kmh": 190.0,
                    "speed_uncertainty_kmh": 8.0,
                    "physics_valid": False,
                    "quality_label": "low_confidence",
                    "stability_label": "unstable_observation",
                    "rejection_reason": "unstable_observation",
                    "speed_source": "fixed_lag_rts_backfill",
                    "fixed_lag_backfilled": True,
                    "id_switch_risk": 0.1,
                    "track_age_frames": 10,
                },
            ],
        },
    ]

    updated = annotate_vehicle_speed_reports(reports, reconstruction_applied=True)
    rejected_track = updated[0]["active_tracks"][0]

    assert rejected_track["physics_valid"] is False
    assert rejected_track["vehicle_speed_display_state"] == "rejected_hidden"
    assert rejected_track["speed_display_hidden"] is True


def test_processed_video_without_current_speed_audit_requires_regeneration(
    tmp_path,
) -> None:
    processed_video = tmp_path / "063_processed.mp4"
    processed_video.write_bytes(b"mp4")

    assert processed_video_needs_regeneration(
        processed_video,
        source_commit_value="abc123",
    )

    reports = annotate_vehicle_speed_reports(
        [
            {
                "frame_index": 1,
                "active_tracks": [
                    {
                        "tracker_id": 1,
                        "class_id": 2,
                        "class_name": "car",
                        "speed_kmh": 30.0,
                        "physics_valid": True,
                    },
                ],
            },
        ],
        reconstruction_applied=True,
        source_commit_value="abc123",
    )
    audit = write_vehicle_speed_audit(
        reports,
        clip="063_dense_city.mp4",
        processed_video_path=processed_video,
        diagnostics_dir=tmp_path / "vehicle_speed_diagnostics",
        source_commit_value="abc123",
        regenerated_due_to_stale_audit=True,
    )

    assert audit["regenerated_due_to_stale_audit"] is True
    assert processed_video_needs_regeneration(
        processed_video,
        source_commit_value="abc123",
    ) is False


def test_vehicle_speed_aggregate_enforces_dense_city_acceptance() -> None:
    result = {
        "status": "ok",
        "clip": "063_dense_city.mp4",
        "vehicle_speed_audit": {
            "clip": "063_dense_city.mp4",
            "vehicle_track_samples": 1000,
            "displayable_vehicle_track_samples": 998,
            "vehicle_display_coverage": 0.998,
            "na_by_reason": {"warming_up_hidden": 2},
            "physics_invalid_by_reason": {},
            "fixed_lag_backfill_count": 998,
            "frozen_last_valid_count": 0,
            "speed_jump_p95_kmh": 0.2,
            "max_speed_by_class": {"car": 78.0},
        },
    }

    aggregate = build_vehicle_speed_aggregate([result])

    assert aggregate["vehicle_display_coverage"] == 0.998
    assert aggregate["na_by_reason"] == {"warming_up_hidden": 2}
    assert aggregate["fixed_lag_backfill_count"] == 998
    assert aggregate["passes_dense_city_acceptance"] is True
    assert aggregate["clip_rows"][0]["passes_vehicle_speed_acceptance"] is True


def test_vehicle_speed_aggregate_fails_hard_speed_limit() -> None:
    result = {
        "status": "ok",
        "clip": "063_dense_city.mp4",
        "vehicle_speed_audit": {
            "clip": "063_dense_city.mp4",
            "vehicle_track_samples": 1000,
            "displayable_vehicle_track_samples": 1000,
            "vehicle_display_coverage": 1.0,
            "max_speed_by_class": {"car": 180.0},
        },
    }

    aggregate = build_vehicle_speed_aggregate([result])

    assert aggregate["passes_dense_city_acceptance"] is False
    assert aggregate["clip_rows"][0]["passes_vehicle_speed_acceptance"] is False


def test_vehicle_speed_aggregate_uses_aggregate_dense_city_threshold() -> None:
    results = [
        {
            "status": "ok",
            "clip": "055_dense_city.mp4",
            "vehicle_speed_audit": {
                "clip": "055_dense_city.mp4",
                "vehicle_track_samples": 1000,
                "displayable_vehicle_track_samples": 994,
                "vehicle_display_coverage": 0.994,
                "na_by_reason": {"warming_up_hidden": 6},
                "max_speed_by_class": {"car": 90.0},
            },
        },
        {
            "status": "ok",
            "clip": "063_dense_city.mp4",
            "vehicle_speed_audit": {
                "clip": "063_dense_city.mp4",
                "vehicle_track_samples": 1000,
                "displayable_vehicle_track_samples": 1000,
                "vehicle_display_coverage": 1.0,
                "na_by_reason": {},
                "max_speed_by_class": {"car": 75.0},
            },
        },
    ]

    aggregate = build_vehicle_speed_aggregate(results)

    assert aggregate["vehicle_display_coverage"] == 0.997
    assert aggregate["clip_rows"][0]["passes_vehicle_speed_acceptance"] is False
    assert aggregate["passes_dense_city_acceptance"] is True
