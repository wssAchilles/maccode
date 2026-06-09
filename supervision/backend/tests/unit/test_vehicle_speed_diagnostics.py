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


def test_vehicle_speed_freeze_window_does_not_self_refresh_past_limit() -> None:
    reports = [
        {
            "frame_index": 0,
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
                    "track_age_frames": 20,
                },
            ],
        },
        {
            "frame_index": 15,
            "active_tracks": [
                {
                    "tracker_id": 7,
                    "class_id": 2,
                    "class_name": "car",
                    "speed_kmh": None,
                    "physics_valid": False,
                    "quality_label": "low_confidence",
                    "track_age_frames": 20,
                },
            ],
        },
        {
            "frame_index": 16,
            "active_tracks": [
                {
                    "tracker_id": 7,
                    "class_id": 2,
                    "class_name": "car",
                    "speed_kmh": None,
                    "physics_valid": False,
                    "quality_label": "low_confidence",
                    "track_age_frames": 20,
                },
            ],
        },
    ]

    updated = annotate_vehicle_speed_reports(reports, reconstruction_applied=True)
    frozen_track = updated[1]["active_tracks"][0]
    hidden_track = updated[2]["active_tracks"][0]
    audit = build_vehicle_speed_audit(updated)

    assert frozen_track["speed_source"] == "frozen_last_valid"
    assert frozen_track["vehicle_speed_display_state"] == "frozen_last_valid"
    assert hidden_track["speed_kmh"] is None
    assert hidden_track["physics_valid"] is False
    assert hidden_track["vehicle_speed_display_state"] == "rejected_hidden"
    assert audit["max_consecutive_frozen_frames"] == 1


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


def test_vehicle_speed_reports_hide_hard_rejected_displayable_speed() -> None:
    reports = [
        {
            "frame_index": 1,
            "active_tracks": [
                {
                    "tracker_id": 8,
                    "class_id": 2,
                    "class_name": "car",
                    "speed_kmh": 180.0,
                    "physics_valid": True,
                    "quality_label": "rejected",
                    "rejection_reason": "class_speed_limit",
                    "track_age_frames": 12,
                },
            ],
        },
    ]

    updated = annotate_vehicle_speed_reports(reports, reconstruction_applied=True)
    track = updated[0]["active_tracks"][0]
    audit = build_vehicle_speed_audit(updated)

    assert track["physics_valid"] is False
    assert track["vehicle_speed_display_state"] == "rejected_hidden"
    assert track["speed_display_hidden"] is True
    assert audit["hard_rejected_display_count"] == 0


def test_vehicle_speed_audit_counts_quality_risk_metrics() -> None:
    reports = annotate_vehicle_speed_reports(
        [
            {
                "frame_index": 1,
                "timestamp_sec": 0.0,
                "active_tracks": [
                    {
                        "tracker_id": 1,
                        "class_id": 2,
                        "class_name": "car",
                        "speed_kmh": 40.0,
                        "speed_uncertainty_kmh": 26.0,
                        "speed_confidence": 0.1,
                        "speed_confidence_interval_kmh": [20.0, 55.0],
                        "acceleration_mps2": 0.4,
                        "jerk_p95_mps3": 0.1,
                        "physics_valid": True,
                        "measurement_source": "vehicle_bottom_center",
                        "contact_pixel_covariance": [[4.0, 0.0], [0.0, 4.0]],
                    },
                ],
            },
            {
                "frame_index": 2,
                "timestamp_sec": 1.0,
                "active_tracks": [
                    {
                        "tracker_id": 1,
                        "class_id": 2,
                        "class_name": "car",
                        "speed_kmh": 42.0,
                        "speed_uncertainty_kmh": 2.0,
                        "speed_confidence": 0.9,
                        "physics_valid": True,
                        "speed_source": "frozen_last_valid",
                    },
                ],
            },
        ],
        reconstruction_applied=True,
    )

    audit = build_vehicle_speed_audit(reports)

    assert audit["displayed_low_confidence_count"] == 1
    assert audit["displayed_high_uncertainty_count"] == 1
    assert audit["displayed_low_confidence_ratio"] == 0.5
    assert audit["displayed_high_uncertainty_ratio"] == 0.5
    assert audit["frozen_ratio"] == 0.5
    assert audit["max_consecutive_frozen_frames"] == 1
    assert audit["contact_point_source_counts"]["vehicle_bottom_center"] == 1
    assert audit["acceleration_p95_mps2"] is not None


def test_vehicle_speed_reports_hide_bbox_center_fallback_low_confidence_speed() -> None:
    reports = [
        {
            "frame_index": 1,
            "active_tracks": [
                {
                    "tracker_id": 2,
                    "class_id": 2,
                    "class_name": "car",
                    "speed_kmh": 35.0,
                    "speed_confidence": 0.1,
                    "speed_uncertainty_kmh": 3.0,
                    "physics_valid": True,
                    "measurement_source": "bbox_center",
                },
            ],
        },
    ]

    updated = annotate_vehicle_speed_reports(reports, reconstruction_applied=True)
    track = updated[0]["active_tracks"][0]

    assert track["bbox_center_fallback"] is True
    assert track["physics_valid"] is False
    assert track["vehicle_speed_display_state"] == "rejected_hidden"


def test_vehicle_speed_reports_downgrade_bbox_center_fallback_high_confidence_speed() -> None:
    reports = [
        {
            "frame_index": 1,
            "active_tracks": [
                {
                    "tracker_id": 2,
                    "class_id": 2,
                    "class_name": "car",
                    "speed_kmh": 35.0,
                    "speed_confidence": 0.9,
                    "speed_uncertainty_kmh": 3.0,
                    "physics_valid": True,
                    "measurement_source": "bbox_center",
                },
            ],
        },
    ]

    updated = annotate_vehicle_speed_reports(reports, reconstruction_applied=True)
    track = updated[0]["active_tracks"][0]
    audit = build_vehicle_speed_audit(updated)

    assert track["bbox_center_fallback"] is True
    assert track["speed_confidence"] < 0.15
    assert track["speed_uncertainty_kmh"] > 25.0
    assert track["physics_valid"] is False
    assert track["speed_display_hidden"] is True
    assert audit["displayable_vehicle_track_samples"] == 0
    assert audit["bbox_center_fallback_count"] == 1


def test_vehicle_speed_reports_tolerate_negative_contact_covariance() -> None:
    reports = [
        {
            "frame_index": 1,
            "active_tracks": [
                {
                    "tracker_id": 2,
                    "class_id": 2,
                    "class_name": "car",
                    "speed_kmh": 35.0,
                    "speed_confidence": 0.9,
                    "speed_uncertainty_kmh": 3.0,
                    "physics_valid": True,
                    "measurement_source": "contact_point_fusion",
                    "contact_pixel_covariance": [[-4.0, 0.0], [0.0, -4.0]],
                },
            ],
        },
    ]

    updated = annotate_vehicle_speed_reports(reports, reconstruction_applied=True)
    track = updated[0]["active_tracks"][0]

    assert track["contact_point_uncertainty_px"] == 0.0
    assert track["physics_valid"] is True


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


def test_vehicle_speed_reports_do_not_recalibrate_bbox_center_fixed_lag_rts_track() -> None:
    reports = []
    for index, speed in enumerate([36.0, 36.2, 36.1, 36.3, 36.2, 36.4], start=1):
        reports.append(
            {
                "frame_index": index,
                "timestamp_sec": index / 30.0,
                "active_tracks": [
                    {
                        "tracker_id": 10,
                        "class_id": 2,
                        "class_name": "car",
                        "speed_kmh": speed,
                        "speed_uncertainty_kmh": 60.0,
                        "speed_confidence": 0.05,
                        "physics_valid": False,
                        "quality_label": "low_confidence",
                        "stability_label": "unstable_observation",
                        "rejection_reason": "unstable_observation",
                        "speed_source": "fixed_lag_rts_backfill",
                        "fixed_lag_backfilled": True,
                        "id_switch_risk": 0.1,
                        "measurement_source": "bbox_center",
                    },
                ],
            },
        )

    updated = annotate_vehicle_speed_reports(reports, reconstruction_applied=True)
    tracks = [report["active_tracks"][0] for report in updated]
    audit = build_vehicle_speed_audit(updated)

    assert all(track["bbox_center_fallback"] is True for track in tracks)
    assert all(track["speed_display_hidden"] is True for track in tracks)
    assert all(track.get("speed_uncertainty_recalibrated") is not True for track in tracks)
    assert audit["vehicle_display_coverage"] == 0.0
    assert audit["speed_uncertainty_recalibrated_count"] == 0


def test_vehicle_speed_reports_recalibrate_stable_fixed_lag_rts_track() -> None:
    reports = []
    for index, speed in enumerate([36.0, 36.2, 36.1, 36.3, 36.2, 36.4], start=1):
        reports.append(
            {
                "frame_index": index,
                "timestamp_sec": index / 30.0,
                "active_tracks": [
                    {
                        "tracker_id": 10,
                        "class_id": 2,
                        "class_name": "car",
                        "speed_kmh": speed,
                        "speed_uncertainty_kmh": 60.0,
                        "speed_confidence": 0.05,
                        "physics_valid": False,
                        "quality_label": "low_confidence",
                        "stability_label": "unstable_observation",
                        "rejection_reason": "unstable_observation",
                        "speed_source": "fixed_lag_rts_backfill",
                        "fixed_lag_backfilled": True,
                        "id_switch_risk": 0.1,
                        "measurement_source": "contact_point_fusion",
                        "contact_fusion_confidence": 0.75,
                    },
                ],
            },
        )

    updated = annotate_vehicle_speed_reports(reports, reconstruction_applied=True)
    tracks = [report["active_tracks"][0] for report in updated]
    audit = build_vehicle_speed_audit(updated)

    assert all(track["physics_valid"] is True for track in tracks)
    assert all(track["speed_source"] == "fixed_lag_rts_calibrated" for track in tracks)
    assert all(track["speed_uncertainty_kmh"] <= 7.0 for track in tracks)
    assert all(track["speed_confidence"] >= 0.35 for track in tracks)
    assert all(track["speed_uncertainty_recalibrated"] is True for track in tracks)
    assert audit["vehicle_display_coverage"] == 1.0
    assert audit["displayed_high_uncertainty_count"] == 0
    assert audit["displayed_low_confidence_count"] == 0
    assert audit["speed_uncertainty_recalibrated_count"] == 6


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
    assert rejected_track.get("speed_uncertainty_recalibrated") is not True


def test_vehicle_speed_reports_downgrade_stable_world_jump_id_switch_risk() -> None:
    reports = []
    for index, speed in enumerate([40.0, 40.2, 40.1, 40.3, 40.2, 40.4, 40.3, 40.5], start=1):
        track = {
            "tracker_id": 44,
            "class_id": 2,
            "class_name": "car",
            "speed_kmh": speed,
            "speed_uncertainty_kmh": 3.0,
            "speed_confidence": 0.42,
            "physics_valid": True,
            "quality_label": "stable",
            "stability_label": "stable",
            "speed_source": "fixed_lag_rts_backfill",
            "fixed_lag_backfilled": True,
            "bev_risk_level": "trusted",
            "ground_x_m": float(index),
            "ground_y_m": 0.0,
            "contact_fusion_confidence": 0.8,
        }
        if index == 4:
            track.update(
                {
                    "physics_valid": False,
                    "id_switch_risk": 0.92,
                    "integrity_rejection_reason": "world_position_jump",
                    "tracking_integrity_state": "suspected_id_switch",
                },
            )
        reports.append(
            {
                "frame_index": index,
                "timestamp_sec": index / 30.0,
                "active_tracks": [track],
            },
        )

    updated = annotate_vehicle_speed_reports(reports, reconstruction_applied=True)
    reviewed_track = updated[3]["active_tracks"][0]
    audit = build_vehicle_speed_audit(updated)

    assert reviewed_track["physics_valid"] is True
    assert reviewed_track["speed_display_hidden"] is False
    assert reviewed_track["id_switch_risk"] < 0.7
    assert reviewed_track["id_switch_risk_original"] == 0.92
    assert reviewed_track["id_switch_risk_downgraded"] is True
    assert reviewed_track["id_switch_risk_downgrade_reason"] == (
        "stable_rts_world_jump_posterior"
    )
    assert audit["id_switch_risk_diagnostics"]["hidden_count"] == 0


def test_vehicle_speed_reports_do_not_downgrade_class_changed_id_switch_risk() -> None:
    reports = []
    for index, speed in enumerate([40.0, 40.2, 40.1, 40.3, 40.2, 40.4, 40.3, 40.5], start=1):
        track = {
            "tracker_id": 44,
            "class_id": 2,
            "class_name": "car",
            "speed_kmh": speed,
            "speed_uncertainty_kmh": 3.0,
            "speed_confidence": 0.42,
            "physics_valid": True,
            "quality_label": "stable",
            "stability_label": "stable",
            "speed_source": "fixed_lag_rts_backfill",
            "fixed_lag_backfilled": True,
            "bev_risk_level": "trusted",
            "ground_x_m": float(index),
            "ground_y_m": 0.0,
            "contact_fusion_confidence": 0.8,
        }
        if index == 4:
            track.update(
                {
                    "physics_valid": False,
                    "id_switch_risk": 0.92,
                    "integrity_rejection_reason": "class_changed",
                    "tracking_integrity_state": "suspected_id_switch",
                },
            )
        reports.append(
            {
                "frame_index": index,
                "timestamp_sec": index / 30.0,
                "active_tracks": [track],
            },
        )

    updated = annotate_vehicle_speed_reports(reports, reconstruction_applied=True)
    rejected_track = updated[3]["active_tracks"][0]

    assert rejected_track["physics_valid"] is False
    assert rejected_track["speed_display_hidden"] is True
    assert rejected_track.get("id_switch_risk_downgraded") is not True


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


def test_vehicle_speed_audit_reports_safe_coverage_excluding_id_switch_risk() -> None:
    reports = annotate_vehicle_speed_reports(
        [
            {
                "frame_index": 1,
                "active_tracks": [
                    {
                        "tracker_id": 1,
                        "class_id": 2,
                        "class_name": "car",
                        "speed_kmh": 40.0,
                        "physics_valid": True,
                        "quality_label": "stable",
                    },
                    {
                        "tracker_id": 2,
                        "class_id": 2,
                        "class_name": "car",
                        "speed_kmh": 42.0,
                        "physics_valid": True,
                        "quality_label": "stable",
                        "id_switch_risk": 0.9,
                    },
                ],
            },
        ],
        reconstruction_applied=True,
    )

    audit = build_vehicle_speed_audit(reports)

    assert audit["vehicle_track_samples"] == 2
    assert audit["displayable_vehicle_track_samples"] == 1
    assert audit["vehicle_display_coverage"] == 0.5
    assert audit["safe_vehicle_track_samples"] == 1
    assert audit["safe_displayable_vehicle_track_samples"] == 1
    assert audit["safe_vehicle_display_coverage"] == 1.0
    assert audit["unsafe_vehicle_track_samples"] == 1
    assert audit["id_switch_risk_diagnostics"]["hidden_count"] == 1
    assert audit["id_switch_risk_diagnostics"]["hidden_by_class"] == {"car": 1}


def test_vehicle_speed_audit_excludes_unresolved_warmup_from_safe_coverage() -> None:
    reports = annotate_vehicle_speed_reports(
        [
            {
                "frame_index": 1,
                "active_tracks": [
                    {
                        "tracker_id": 3,
                        "class_id": 2,
                        "class_name": "car",
                        "speed_kmh": None,
                        "physics_valid": False,
                        "quality_label": "warming_up",
                        "stability_label": "insufficient_samples",
                        "track_age_frames": 1,
                    },
                ],
            },
        ],
        reconstruction_applied=True,
    )

    audit = build_vehicle_speed_audit(reports)

    assert audit["vehicle_track_samples"] == 1
    assert audit["vehicle_display_coverage"] == 0.0
    assert audit["safe_vehicle_track_samples"] == 0
    assert audit["safe_vehicle_display_coverage"] is None
    assert audit["na_by_reason"] == {"warming_up_hidden": 1}


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


def test_vehicle_speed_aggregate_does_not_treat_zero_safe_samples_as_missing() -> None:
    result = {
        "status": "ok",
        "clip": "063_dense_city.mp4",
        "vehicle_speed_audit": {
            "clip": "063_dense_city.mp4",
            "vehicle_track_samples": 1000,
            "displayable_vehicle_track_samples": 998,
            "vehicle_display_coverage": 0.998,
            "safe_vehicle_track_samples": 0,
            "safe_displayable_vehicle_track_samples": 0,
            "safe_vehicle_display_coverage": None,
            "unsafe_vehicle_track_samples": 1000,
            "max_speed_by_class": {"car": 78.0},
        },
    }

    aggregate = build_vehicle_speed_aggregate([result])

    assert aggregate["safe_vehicle_track_samples"] == 0
    assert aggregate["safe_vehicle_display_coverage"] is None
    assert aggregate["coverage_used_for_acceptance"] is None
    assert aggregate["passes_dense_city_acceptance"] is False
    assert aggregate["clip_rows"][0]["coverage_used_for_acceptance"] is None
    assert aggregate["clip_rows"][0]["passes_vehicle_speed_acceptance"] is False


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


def test_vehicle_speed_aggregate_does_not_allow_safe_coverage_to_mask_total_gap() -> None:
    result = {
        "status": "ok",
        "clip": "065_dense_city.mp4",
        "vehicle_speed_audit": {
            "clip": "065_dense_city.mp4",
            "vehicle_track_samples": 1000,
            "displayable_vehicle_track_samples": 987,
            "vehicle_display_coverage": 0.987,
            "safe_vehicle_track_samples": 987,
            "safe_displayable_vehicle_track_samples": 987,
            "safe_vehicle_display_coverage": 1.0,
            "unsafe_vehicle_track_samples": 13,
            "na_by_reason": {"rejected_hidden": 13},
            "max_speed_by_class": {"car": 75.0},
        },
    }

    aggregate = build_vehicle_speed_aggregate([result])

    assert aggregate["vehicle_display_coverage"] == 0.987
    assert aggregate["safe_vehicle_display_coverage"] == 1.0
    assert aggregate["coverage_used_for_acceptance"] == 0.987
    assert aggregate["passes_dense_city_acceptance"] is False
    assert aggregate["clip_rows"][0]["passes_vehicle_speed_acceptance"] is False
    assert aggregate["hidden_id_switch_risk_count"] == 0


def test_vehicle_speed_aggregate_fails_quality_gate() -> None:
    result = {
        "status": "ok",
        "clip": "063_dense_city.mp4",
        "vehicle_speed_audit": {
            "clip": "063_dense_city.mp4",
            "vehicle_track_samples": 1000,
            "displayable_vehicle_track_samples": 1000,
            "vehicle_display_coverage": 1.0,
            "displayed_high_uncertainty_count": 40,
            "displayed_high_uncertainty_ratio": 0.04,
            "max_speed_by_class": {"car": 80.0},
        },
    }

    aggregate = build_vehicle_speed_aggregate([result])

    assert aggregate["passes_dense_city_acceptance"] is False
    assert aggregate["clip_rows"][0]["passes_vehicle_speed_acceptance"] is False


def test_vehicle_speed_aggregate_fails_low_confidence_quality_gate() -> None:
    result = {
        "status": "ok",
        "clip": "063_dense_city.mp4",
        "vehicle_speed_audit": {
            "clip": "063_dense_city.mp4",
            "vehicle_track_samples": 1000,
            "displayable_vehicle_track_samples": 1000,
            "vehicle_display_coverage": 1.0,
            "displayed_low_confidence_count": 40,
            "displayed_low_confidence_ratio": 0.04,
            "max_speed_by_class": {"car": 80.0},
        },
    }

    aggregate = build_vehicle_speed_aggregate([result])

    assert aggregate["passes_dense_city_acceptance"] is False
    assert aggregate["clip_rows"][0]["passes_vehicle_speed_acceptance"] is False


def test_vehicle_speed_audit_outputs_gt_metrics_when_csv_exists(tmp_path) -> None:
    gt_dir = tmp_path / "speed_ground_truth"
    gt_dir.mkdir()
    (gt_dir / "063_dense_city.csv").write_text(
        "clip,tracker_id,frame_start,frame_end,class_name,gt_speed_kmh,source,confidence\n"
        "063_dense_city.mp4,1,1,2,car,41.0,manual,1.0\n",
        encoding="utf-8",
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
                        "speed_kmh": 40.0,
                        "physics_valid": True,
                        "speed_uncertainty_kmh": 3.0,
                        "speed_confidence": 0.7,
                        "speed_confidence_interval_kmh": [36.0, 44.0],
                    },
                ],
            },
            {
                "frame_index": 2,
                "active_tracks": [
                    {
                        "tracker_id": 1,
                        "class_id": 2,
                        "class_name": "car",
                        "speed_kmh": 42.0,
                        "physics_valid": True,
                        "speed_uncertainty_kmh": 3.0,
                        "speed_confidence": 0.8,
                        "speed_confidence_interval_kmh": [38.0, 46.0],
                    },
                ],
            },
        ],
        reconstruction_applied=True,
    )

    audit = build_vehicle_speed_audit(
        reports,
        clip="063_dense_city.mp4",
        speed_ground_truth_dir=gt_dir,
    )
    metrics = audit["speed_ground_truth_metrics"]

    assert metrics["available"] is True
    assert metrics["matched_count"] == 1
    assert metrics["speed_mae_kmh"] == 0.0
    assert metrics["p90_interval_coverage"] == 1.0
    assert metrics["bias_correction_kmh"] == -0.0
    assert metrics["mean_predicted_uncertainty_kmh"] == 3.0
    assert metrics["suggested_uncertainty_multiplier"] == 0.5
    assert metrics["calibration_status"] == "overconservative_uncertainty"


def test_vehicle_speed_audit_matches_gt_when_track_class_name_is_missing(tmp_path) -> None:
    gt_dir = tmp_path / "speed_ground_truth"
    gt_dir.mkdir()
    (gt_dir / "063_dense_city.csv").write_text(
        "clip,tracker_id,frame_start,frame_end,class_name,gt_speed_kmh,source,confidence\n"
        "063_dense_city.mp4,1,1,1,2,40.0,manual,1.0\n",
        encoding="utf-8",
    )
    reports = annotate_vehicle_speed_reports(
        [
            {
                "frame_index": 1,
                "active_tracks": [
                    {
                        "tracker_id": 1,
                        "class_id": 2,
                        "speed_kmh": 40.0,
                        "physics_valid": True,
                        "speed_uncertainty_kmh": 3.0,
                    },
                ],
            },
        ],
        reconstruction_applied=True,
    )

    metrics = build_vehicle_speed_audit(
        reports,
        clip="063_dense_city.mp4",
        speed_ground_truth_dir=gt_dir,
    )["speed_ground_truth_metrics"]

    assert metrics["matched_count"] == 1
    assert metrics["speed_mae_kmh"] == 0.0


def test_vehicle_speed_audit_outputs_proxy_only_without_gt() -> None:
    audit = build_vehicle_speed_audit([], clip="063_dense_city.mp4")

    assert audit["speed_ground_truth_metrics"]["available"] is False
    assert audit["speed_ground_truth_metrics"]["proxy_only"] is True


def test_vehicle_speed_audit_outputs_vehicle_3d_scale_sanity() -> None:
    reports = annotate_vehicle_speed_reports(
        [
            {
                "frame_index": 1,
                "calibration_diagnostics": {
                    "calibration_3d_diagnostics": {"calibration_trusted": True},
                },
                "active_tracks": [
                    {
                        "tracker_id": 1,
                        "class_id": 2,
                        "class_name": "car",
                        "xyxy": [0.0, 0.0, 100.0, 50.0],
                        "local_scale_factor": 0.02,
                        "ground_y_m": 1.0,
                        "speed_kmh": 40.0,
                        "physics_valid": True,
                    },
                    {
                        "tracker_id": 2,
                        "class_id": 2,
                        "class_name": "car",
                        "xyxy": [0.0, 0.0, 90.0, 50.0],
                        "local_scale_factor": 0.02,
                        "ground_y_m": 10.0,
                        "speed_kmh": 45.0,
                        "physics_valid": True,
                    },
                ],
            },
        ],
        reconstruction_applied=True,
    )

    sanity = build_vehicle_speed_audit(reports)["vehicle_3d_scale_sanity"]

    assert sanity["available"] is True
    assert sanity["calibration_3d_available"] is True
    assert sanity["scale_bias_by_y_depth"]
    assert sanity["bbox_size_consistency_error"] is not None


def test_vehicle_speed_aggregate_reports_vehicle_3d_qa_counts() -> None:
    result = {
        "status": "ok",
        "clip": "063_dense_city.mp4",
        "vehicle_speed_audit": {
            "clip": "063_dense_city.mp4",
            "vehicle_track_samples": 100,
            "displayable_vehicle_track_samples": 100,
            "vehicle_display_coverage": 1.0,
            "max_speed_by_class": {"car": 80.0},
            "vehicle_3d_scale_sanity": {
                "available": True,
                "calibration_region_quality": "review",
                "homography_uncertainty_multiplier": 2.5,
            },
        },
    }

    aggregate = build_vehicle_speed_aggregate([result])

    assert aggregate["vehicle_3d_scale_sanity_available_count"] == 1
    assert aggregate["vehicle_3d_review_clip_count"] == 1
    assert aggregate["vehicle_3d_calibration_region_quality_counts"] == {"review": 1}
    assert aggregate["vehicle_3d_homography_uncertainty_multiplier_p95"] == 2.5
    assert aggregate["clip_rows"][0]["vehicle_3d_calibration_region_quality"] == "review"
