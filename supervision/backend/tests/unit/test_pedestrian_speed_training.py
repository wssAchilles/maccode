from __future__ import annotations

import pickle

from domain.speed.pedestrian_training import (
    build_benchmark_summary,
    build_training_manifest,
    filter_manifest_to_existing_clips,
    generate_pseudo_labels,
    train_contact_quality_model,
    train_speed_validity_model,
    write_training_outputs,
)


def test_manifest_declares_033_039_train_and_040_042_validation() -> None:
    manifest = build_training_manifest()

    assert [item.clip_id for item in manifest if item.split == "train"] == list(range(33, 40))
    assert [item.clip_id for item in manifest if item.split == "validation"] == [40, 41, 42]
    assert manifest[8].clip_name == "041_pedestrian_crowd_high_view_0240s_30s.mp4"
    assert {item.camera_profile_id for item in manifest} == {"pedestrian_high_view_camera"}


def test_manifest_can_skip_missing_source_clips(tmp_path) -> None:
    manifest = build_training_manifest()
    for item in manifest:
        if item.clip_id != 41:
            (tmp_path / item.clip_name).write_bytes(b"mp4")

    available, missing = filter_manifest_to_existing_clips(tmp_path, manifest)

    assert [item.clip_id for item in available] == [33, 34, 35, 36, 37, 38, 39, 40, 42]
    assert [item.clip_id for item in missing] == [41]


def test_generate_pseudo_labels_contains_contact_speed_and_identity_labels() -> None:
    rows = generate_pseudo_labels(_payloads(), build_training_manifest())

    assert rows
    assert {row.contact_quality_label for row in rows} >= {"stance", "polluted"}
    assert {row.speed_quality_label for row in rows} >= {"valid", "uncertain", "rejected"}
    assert {row.id_continuity_label for row in rows} >= {"fragmented", "switch_risk"}
    assert all(row.clip.startswith(("033_", "040_")) for row in rows)
    assert any(row.speed_source == "fixed_lag_rts_backfill" for row in rows)


def test_quality_models_score_clean_rows_higher_than_rejected_rows() -> None:
    rows = generate_pseudo_labels(_payloads(), build_training_manifest())
    contact_model = train_contact_quality_model(rows)
    speed_model = train_speed_validity_model(rows)

    clean = next(row for row in rows if row.speed_quality_label == "valid")
    rejected = next(row for row in rows if row.speed_quality_label == "rejected")

    assert contact_model.predict_score(clean.__dict__) > contact_model.predict_score(
        rejected.__dict__,
    )
    assert speed_model.predict_score(clean.__dict__) > speed_model.predict_score(
        rejected.__dict__,
    )


def test_benchmark_summary_reports_clip_and_aggregate_metrics() -> None:
    rows = generate_pseudo_labels(_payloads(), build_training_manifest())
    summary = build_benchmark_summary(rows)

    assert summary["clip_count"] == 2
    assert "033_pedestrian_crowd_high_view_0000s_30s.mp4" in summary["by_clip"]
    assert "train" in summary["aggregate"]
    assert "validation" in summary["aggregate"]
    assert summary["aggregate"]["train"]["person_speed_coverage"] > 0.0
    assert summary["aggregate"]["train"]["max_pedestrian_speed_kmh"] <= 18.0
    assert set(summary["tracker_variants"]) == {
        "bytetrack_current",
        "ocsort_recovery",
        "botsort_reid_offline",
    }
    assert summary["model_evaluation"]["speed_validity_model"]["coverage_policy"]
    assert summary["offline_world_motion_reference"]["fallback"] == (
        "existing_geometry_contact_pipeline"
    )


def test_write_training_outputs_uses_jsonl_without_pyarrow(tmp_path) -> None:
    rows = generate_pseudo_labels(_payloads(), build_training_manifest())
    paths = write_training_outputs(rows, tmp_path, build_training_manifest())

    assert paths["manifest"].name == "train_manifest.json"
    assert paths["pseudo_label_format"] in {"jsonl", "parquet"}
    assert paths["manual_audit_samples"].exists()
    assert paths["benchmark_summary"].exists()

    contact_model = pickle.loads(paths["contact_quality_model"].read_bytes())
    speed_model = pickle.loads(paths["speed_validity_model"].read_bytes())
    assert contact_model.name == "ContactQualityModel"
    assert speed_model.name == "SpeedValidityModel"


def _payloads() -> dict[str, dict[str, object]]:
    return {
        "033_pedestrian_crowd_high_view_0000s_30s.mp4": {
            "frame_reports": [
                _report(
                    1,
                    [
                        _track(7, speed=4.8, contact_state="double_support"),
                        _track(8, speed=None, measurement_policy="reject"),
                    ],
                ),
                _report(
                    3,
                    [
                        _track(
                            7,
                            speed=5.2,
                            reconstructed=True,
                            contact_state="left_stance",
                        ),
                        _track(
                            8,
                            speed=3.0,
                            physics_valid=False,
                            contact_state="swing",
                        ),
                    ],
                ),
            ],
        },
        "040_pedestrian_crowd_high_view_0210s_30s.mp4": {
            "frame_reports": [
                _report(
                    1,
                    [
                        _track(
                            21,
                            speed=6.0,
                            id_switch_risk=0.8,
                            association_rejection_reason="bev_gate",
                        ),
                    ],
                ),
            ],
        },
    }


def _report(frame_index: int, tracks: list[dict[str, object]]) -> dict[str, object]:
    return {
        "frame_index": frame_index,
        "timestamp_sec": frame_index / 25.0,
        "active_tracks": tracks,
    }


def _track(
    tracker_id: int,
    *,
    speed: float | None,
    physics_valid: bool = True,
    contact_state: str = "double_support",
    measurement_policy: str = "update",
    reconstructed: bool = False,
    id_switch_risk: float | None = None,
    association_rejection_reason: str | None = None,
) -> dict[str, object]:
    return {
        "tracker_id": tracker_id,
        "class_id": 0,
        "class_name": "person",
        "confidence": 0.8,
        "xyxy": [10.0, 20.0, 50.0, 140.0],
        "speed_kmh": speed,
        "speed_uncertainty_kmh": 1.0 if speed is not None else None,
        "speed_confidence": 0.75 if physics_valid else 0.2,
        "physics_valid": physics_valid,
        "track_age_frames": 12,
        "acceleration_mps2": 0.1,
        "measurement_policy": measurement_policy,
        "measurement_confidence": 0.8 if measurement_policy == "update" else 0.1,
        "contact_state": contact_state,
        "contact_fusion_confidence": 0.85 if measurement_policy == "update" else 0.1,
        "contact_confidence": 0.8 if measurement_policy == "update" else 0.1,
        "optical_flow_inlier_ratio": 0.8 if measurement_policy == "update" else 0.1,
        "id_switch_risk": id_switch_risk,
        "association_rejection_reason": association_rejection_reason,
        "reconstructed": reconstructed,
        "imm_speed_kmh": speed,
    }
