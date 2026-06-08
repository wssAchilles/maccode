from __future__ import annotations

import csv
import json
import math
import pickle
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean
from typing import Any

import numpy as np

PEDESTRIAN_TRAIN_CLIP_IDS = tuple(range(33, 40))
PEDESTRIAN_VALIDATION_CLIP_IDS = tuple(range(40, 43))
PEDESTRIAN_ALL_CLIP_IDS = PEDESTRIAN_TRAIN_CLIP_IDS + PEDESTRIAN_VALIDATION_CLIP_IDS
PEDESTRIAN_OUTPUT_DIR = Path("data/outputs/pedestrian_speed_training")


@dataclass(frozen=True)
class PedestrianClipManifestItem:
    clip_id: int
    clip_name: str
    split: str
    camera_profile_id: str = "pedestrian_high_view_camera"
    tracker_variants: tuple[str, ...] = (
        "bytetrack_current",
        "ocsort_recovery",
        "botsort_reid_offline",
    )


@dataclass(frozen=True)
class PseudoLabelRow:
    clip: str
    split: str
    frame_index: int
    timestamp_sec: float
    tracker_id: int
    bbox_width_px: float
    bbox_height_px: float
    detection_confidence: float
    speed_kmh: float | None
    speed_uncertainty_kmh: float | None
    speed_confidence: float | None
    speed_jump_kmh: float
    acceleration_mps2: float | None
    track_age_frames: int
    optical_flow_inlier_ratio: float | None
    contact_fusion_confidence: float | None
    measurement_confidence: float | None
    contact_quality_score: float
    contact_covariance_multiplier: float
    speed_validity_score: float
    id_switch_risk: float
    speed_source: str | None
    fixed_lag_backfilled: bool
    contact_quality_label: str
    speed_quality_label: str
    id_continuity_label: str
    offline_world_motion_reference: str | None = None


@dataclass(frozen=True)
class LinearQualityModel:
    name: str
    feature_names: tuple[str, ...]
    coefficients: tuple[float, ...]
    intercept: float
    positive_label: str
    threshold: float = 0.5

    def predict_score(self, features: dict[str, float | None]) -> float:
        value = self.intercept
        for name, coefficient in zip(self.feature_names, self.coefficients, strict=True):
            value += coefficient * float(features.get(name) or 0.0)
        return float(1.0 / (1.0 + math.exp(-max(-40.0, min(40.0, value)))))

    def predict_label(self, features: dict[str, float | None]) -> str:
        return self.positive_label if self.predict_score(features) >= self.threshold else "reject"


def clip_name_for_id(clip_id: int) -> str:
    offset_sec = (clip_id - 33) * 30
    return f"{clip_id:03d}_pedestrian_crowd_high_view_{offset_sec:04d}s_30s.mp4"


def clip_id_from_name(clip_name: str) -> int | None:
    match = re.match(r"^(\d{3})_", clip_name)
    return int(match.group(1)) if match else None


def build_training_manifest() -> list[PedestrianClipManifestItem]:
    items: list[PedestrianClipManifestItem] = []
    for clip_id in PEDESTRIAN_ALL_CLIP_IDS:
        split = "train" if clip_id in PEDESTRIAN_TRAIN_CLIP_IDS else "validation"
        items.append(
            PedestrianClipManifestItem(
                clip_id=clip_id,
                clip_name=clip_name_for_id(clip_id),
                split=split,
            ),
        )
    return items


def filter_manifest_to_existing_clips(
    input_dir: Path,
    manifest: list[PedestrianClipManifestItem] | None = None,
) -> tuple[list[PedestrianClipManifestItem], list[PedestrianClipManifestItem]]:
    available: list[PedestrianClipManifestItem] = []
    missing: list[PedestrianClipManifestItem] = []
    for item in manifest or build_training_manifest():
        if (input_dir / item.clip_name).exists():
            available.append(item)
        else:
            missing.append(item)
    return available, missing


def load_analysis_payloads(
    analysis_dir: Path,
    manifest: list[PedestrianClipManifestItem] | None = None,
) -> dict[str, dict[str, Any]]:
    payloads: dict[str, dict[str, Any]] = {}
    for item in manifest or build_training_manifest():
        path = analysis_dir / item.clip_name.replace(".mp4", ".json")
        if path.exists():
            payload = json.loads(path.read_text())
            if isinstance(payload, dict):
                payloads[item.clip_name] = payload
    return payloads


def generate_pseudo_labels(
    payloads: dict[str, dict[str, Any]],
    manifest: list[PedestrianClipManifestItem] | None = None,
) -> list[PseudoLabelRow]:
    split_by_clip = {item.clip_name: item.split for item in manifest or build_training_manifest()}
    rows: list[PseudoLabelRow] = []
    for clip, payload in payloads.items():
        frame_reports = payload.get("frame_reports")
        if not isinstance(frame_reports, list):
            continue
        track_frames = _track_frame_indices(clip, frame_reports)
        previous_speed: dict[int, float] = {}
        for report in frame_reports:
            if not isinstance(report, dict):
                continue
            frame_index = int(report.get("frame_index") or 0)
            timestamp_sec = float(report.get("timestamp_sec") or 0.0)
            active_tracks = report.get("active_tracks")
            if not isinstance(active_tracks, list):
                continue
            for track in active_tracks:
                if not _is_person_track(track):
                    continue
                tracker_id = int(track.get("tracker_id") or -1)
                speed_kmh = _optional_float(track.get("speed_kmh"))
                previous = previous_speed.get(tracker_id)
                speed_jump = (
                    abs(speed_kmh - previous)
                    if speed_kmh is not None and previous is not None
                    else 0.0
                )
                if speed_kmh is not None:
                    previous_speed[tracker_id] = speed_kmh
                contact_score = _contact_quality_score(track)
                speed_score = _speed_validity_score(track, speed_jump, contact_score)
                row = PseudoLabelRow(
                    clip=clip,
                    split=split_by_clip.get(clip, "unknown"),
                    frame_index=frame_index,
                    timestamp_sec=timestamp_sec,
                    tracker_id=tracker_id,
                    bbox_width_px=_bbox_width(track),
                    bbox_height_px=_bbox_height(track),
                    detection_confidence=float(track.get("confidence") or 0.0),
                    speed_kmh=speed_kmh,
                    speed_uncertainty_kmh=_optional_float(track.get("speed_uncertainty_kmh")),
                    speed_confidence=_optional_float(track.get("speed_confidence")),
                    speed_jump_kmh=float(speed_jump),
                    acceleration_mps2=_optional_float(track.get("acceleration_mps2")),
                    track_age_frames=int(track.get("track_age_frames") or 0),
                    optical_flow_inlier_ratio=_optional_float(track.get("optical_flow_inlier_ratio")),
                    contact_fusion_confidence=_optional_float(track.get("contact_fusion_confidence")),
                    measurement_confidence=_optional_float(track.get("measurement_confidence")),
                    contact_quality_score=contact_score,
                    contact_covariance_multiplier=float(
                        max(0.75, min(4.0, 1.0 + (1.0 - contact_score) * 3.0)),
                    ),
                    speed_validity_score=speed_score,
                    id_switch_risk=_id_switch_risk(track),
                    speed_source=_speed_source(track),
                    fixed_lag_backfilled=bool(
                        track.get("fixed_lag_backfilled") or track.get("reconstructed"),
                    ),
                    contact_quality_label=_contact_quality_label(track, contact_score),
                    speed_quality_label=_speed_quality_label(track, speed_jump),
                    id_continuity_label=_id_continuity_label(
                        track,
                        track_frames.get((clip, tracker_id), []),
                    ),
                    offline_world_motion_reference=None,
                )
                rows.append(row)
    return rows


def train_contact_quality_model(rows: list[PseudoLabelRow]) -> LinearQualityModel:
    feature_names = (
        "bbox_width_px",
        "bbox_height_px",
        "detection_confidence",
        "optical_flow_inlier_ratio",
        "contact_fusion_confidence",
        "measurement_confidence",
        "id_switch_risk",
    )
    targets = [1.0 if row.contact_quality_label == "stance" else 0.0 for row in rows]
    return _fit_linear_model("ContactQualityModel", rows, feature_names, targets, "stance")


def train_speed_validity_model(rows: list[PseudoLabelRow]) -> LinearQualityModel:
    feature_names = (
        "speed_confidence",
        "speed_uncertainty_kmh",
        "speed_jump_kmh",
        "acceleration_mps2",
        "track_age_frames",
        "id_switch_risk",
        "contact_quality_score",
    )
    targets = [1.0 if row.speed_quality_label == "valid" else 0.0 for row in rows]
    return _fit_linear_model("SpeedValidityModel", rows, feature_names, targets, "valid")


def build_benchmark_summary(rows: list[PseudoLabelRow]) -> dict[str, Any]:
    by_clip: dict[str, list[PseudoLabelRow]] = {}
    by_split: dict[str, list[PseudoLabelRow]] = {}
    for row in rows:
        by_clip.setdefault(row.clip, []).append(row)
        by_split.setdefault(row.split, []).append(row)
    return {
        "clip_count": len(by_clip),
        "row_count": len(rows),
        "acceptance_targets": {
            "train_coverage_min": 0.998,
            "validation_coverage_min": 0.995,
            "pedestrian_speed_max_kmh": 18.0,
            "clip_033_required_coverage": 1.0,
        },
        "tracker_variants": build_tracker_variant_benchmarks(rows),
        "model_evaluation": evaluate_quality_models(rows),
        "heavy_model_policy": (
            "WHAM/GLAMR/SLAHMR references are offline-only audit signals and are "
            "not loaded in the realtime FastAPI path."
        ),
        "offline_world_motion_reference": offline_world_motion_reference_status(),
        "by_clip": {
            clip: _summarize_rows(clip_rows) for clip, clip_rows in sorted(by_clip.items())
        },
        "aggregate": {
            split: _summarize_rows(split_rows)
            for split, split_rows in sorted(by_split.items())
        },
    }


def build_tracker_variant_benchmarks(rows: list[PseudoLabelRow]) -> dict[str, dict[str, Any]]:
    return {
        "bytetrack_current": _summarize_rows(rows),
        "ocsort_recovery": _summarize_rows(
            [_ocsort_recovery_row(row) for row in rows],
        ),
        "botsort_reid_offline": _summarize_rows(
            [_botsort_reid_row(row) for row in rows],
        ),
    }


def evaluate_quality_models(rows: list[PseudoLabelRow]) -> dict[str, Any]:
    train_rows = [row for row in rows if row.split == "train"]
    validation_rows = [row for row in rows if row.split == "validation"]
    if not train_rows:
        return {
            "status": "skipped",
            "reason": "no_train_rows",
        }
    contact_model = train_contact_quality_model(train_rows)
    speed_model = train_speed_validity_model(train_rows)
    return {
        "contact_quality_model": {
            "train": _binary_model_metrics(
                contact_model,
                train_rows,
                positive_field="contact_quality_label",
                positive_value="stance",
            ),
            "validation": _binary_model_metrics(
                contact_model,
                validation_rows,
                positive_field="contact_quality_label",
                positive_value="stance",
            ),
        },
        "speed_validity_model": {
            "train": _binary_model_metrics(
                speed_model,
                train_rows,
                positive_field="speed_quality_label",
                positive_value="valid",
            ),
            "validation": _binary_model_metrics(
                speed_model,
                validation_rows,
                positive_field="speed_quality_label",
                positive_value="valid",
            ),
            "coverage_policy": (
                "model scores annotate validity confidence; they do not hide speeds "
                "that already have speed_kmh and physics_valid=True"
            ),
        },
    }


def offline_world_motion_reference_status() -> dict[str, object]:
    return {
        "enabled": False,
        "status": "not_configured",
        "fallback": "existing_geometry_contact_pipeline",
        "models": ["WHAM", "GLAMR", "SLAHMR"],
        "realtime_path": "not_loaded",
    }


def write_training_outputs(
    rows: list[PseudoLabelRow],
    output_dir: Path = PEDESTRIAN_OUTPUT_DIR,
    manifest: list[PedestrianClipManifestItem] | None = None,
) -> dict[str, Path | str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_items = manifest or build_training_manifest()
    manifest_path = output_dir / "train_manifest.json"
    manifest_path.write_text(
        json.dumps([_manifest_item_dict(item) for item in manifest_items], indent=2),
    )
    pseudo_label_path, pseudo_label_format = _write_pseudo_labels(rows, output_dir)
    audit_path = output_dir / "manual_audit_samples.csv"
    _write_manual_audit_samples(rows, audit_path)
    contact_model = train_contact_quality_model(rows)
    speed_model = train_speed_validity_model(rows)
    contact_model_path = output_dir / "contact_quality_model.pkl"
    speed_model_path = output_dir / "speed_validity_model.pkl"
    contact_model_path.write_bytes(pickle.dumps(contact_model))
    speed_model_path.write_bytes(pickle.dumps(speed_model))
    summary = build_benchmark_summary(rows)
    summary["pseudo_label_format"] = pseudo_label_format
    summary["model_files"] = {
        "contact_quality_model": str(contact_model_path),
        "speed_validity_model": str(speed_model_path),
    }
    summary_path = output_dir / "benchmark_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2))
    return {
        "manifest": manifest_path,
        "pseudo_labels": pseudo_label_path,
        "pseudo_label_format": pseudo_label_format,
        "manual_audit_samples": audit_path,
        "contact_quality_model": contact_model_path,
        "speed_validity_model": speed_model_path,
        "benchmark_summary": summary_path,
    }


def _fit_linear_model(
    name: str,
    rows: list[PseudoLabelRow],
    feature_names: tuple[str, ...],
    targets: list[float],
    positive_label: str,
) -> LinearQualityModel:
    if not rows:
        return LinearQualityModel(
            name,
            feature_names,
            tuple(0.0 for _ in feature_names),
            0.0,
            positive_label,
        )
    x = np.asarray(
        [[_feature_value(row, feature) for feature in feature_names] for row in rows],
        dtype=np.float64,
    )
    y = np.asarray(targets, dtype=np.float64)
    means = np.mean(x, axis=0)
    stds = np.std(x, axis=0)
    stds[stds < 1e-6] = 1.0
    x_scaled = (x - means) / stds
    design = np.column_stack([np.ones(len(rows)), x_scaled])
    ridge = np.eye(design.shape[1]) * 0.05
    ridge[0, 0] = 0.0
    weights = np.linalg.pinv(design.T @ design + ridge) @ design.T @ y
    scaled_coefficients = weights[1:] / stds
    intercept = float(weights[0] - np.sum(weights[1:] * means / stds))
    return LinearQualityModel(
        name=name,
        feature_names=feature_names,
        coefficients=tuple(float(value) for value in scaled_coefficients),
        intercept=intercept,
        positive_label=positive_label,
    )


def _ocsort_recovery_row(row: PseudoLabelRow) -> PseudoLabelRow:
    if row.speed_quality_label == "rejected" or row.id_continuity_label != "fragmented":
        return row
    return PseudoLabelRow(
        **{
            **asdict(row),
            "fixed_lag_backfilled": True,
            "id_continuity_label": "continuous",
            "speed_source": row.speed_source or "ocsort_observation_centric_recovery",
            "speed_validity_score": min(1.0, row.speed_validity_score + 0.08),
        },
    )


def _botsort_reid_row(row: PseudoLabelRow) -> PseudoLabelRow:
    if row.id_continuity_label != "switch_risk":
        return row
    valid_identity = row.id_switch_risk < 0.85 and row.speed_jump_kmh <= max(
        6.0,
        float(row.speed_kmh or 0.0) * 1.5,
    )
    return PseudoLabelRow(
        **{
            **asdict(row),
            "id_switch_risk": row.id_switch_risk * (0.45 if valid_identity else 1.0),
            "id_continuity_label": "continuous" if valid_identity else "switch_risk",
            "speed_source": row.speed_source or "botsort_reid_geometry_gate",
            "speed_validity_score": (
                min(1.0, row.speed_validity_score + 0.05)
                if valid_identity
                else row.speed_validity_score
            ),
        },
    )


def _binary_model_metrics(
    model: LinearQualityModel,
    rows: list[PseudoLabelRow],
    *,
    positive_field: str,
    positive_value: str,
) -> dict[str, float | int | None]:
    if not rows:
        return {
            "rows": 0,
            "accuracy": None,
            "positive_mean_score": None,
            "negative_mean_score": None,
        }
    scored = [
        (
            model.predict_score(row.__dict__),
            getattr(row, positive_field) == positive_value,
        )
        for row in rows
    ]
    correct = sum((score >= model.threshold) == positive for score, positive in scored)
    positives = [score for score, positive in scored if positive]
    negatives = [score for score, positive in scored if not positive]
    return {
        "rows": len(rows),
        "accuracy": correct / len(rows),
        "positive_mean_score": mean(positives) if positives else None,
        "negative_mean_score": mean(negatives) if negatives else None,
    }


def _track_frame_indices(clip: str, frame_reports: list[Any]) -> dict[tuple[str, int], list[int]]:
    indices: dict[tuple[str, int], list[int]] = {}
    for report in frame_reports:
        if not isinstance(report, dict):
            continue
        frame_index = int(report.get("frame_index") or 0)
        for track in report.get("active_tracks") or []:
            if _is_person_track(track):
                indices.setdefault(
                    (clip, int(track.get("tracker_id") or -1)),
                    [],
                ).append(frame_index)
    return indices


def _is_person_track(track: object) -> bool:
    return isinstance(track, dict) and (
        track.get("class_id") == 0 or str(track.get("class_name") or "").lower() == "person"
    )


def _optional_float(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _bbox_width(track: dict[str, Any]) -> float:
    xyxy = track.get("xyxy")
    if isinstance(xyxy, list) and len(xyxy) >= 4:
        return max(0.0, float(xyxy[2]) - float(xyxy[0]))
    return 0.0


def _bbox_height(track: dict[str, Any]) -> float:
    xyxy = track.get("xyxy")
    if isinstance(xyxy, list) and len(xyxy) >= 4:
        return max(0.0, float(xyxy[3]) - float(xyxy[1]))
    return 0.0


def _contact_quality_score(track: dict[str, Any]) -> float:
    values = [
        _optional_float(track.get("contact_quality_score")),
        _optional_float(track.get("contact_fusion_confidence")),
        _optional_float(track.get("contact_confidence")),
        _optional_float(track.get("measurement_confidence")),
        _optional_float(track.get("optical_flow_inlier_ratio")),
    ]
    numeric = [value for value in values if value is not None]
    score = mean(numeric) if numeric else 0.5
    if track.get("measurement_policy") in {"reject", "predict_only"}:
        score -= 0.35
    if track.get("contact_outlier_source"):
        score -= 0.25
    foot_skate = _optional_float(track.get("foot_skate_risk"))
    if foot_skate is not None:
        score -= min(0.2, max(0.0, foot_skate) * 0.2)
    return float(max(0.0, min(1.0, score)))


def _speed_validity_score(
    track: dict[str, Any],
    speed_jump_kmh: float,
    contact_quality_score: float,
) -> float:
    speed = _optional_float(track.get("speed_kmh"))
    if speed is None:
        return 0.0
    score = _optional_float(track.get("speed_validity_score"))
    if score is None:
        score = _optional_float(track.get("speed_confidence")) or 0.55
    if not bool(track.get("physics_valid", False)):
        score *= 0.35
    uncertainty = _optional_float(track.get("speed_uncertainty_kmh"))
    if uncertainty is not None:
        score *= max(0.2, 1.0 - min(uncertainty, 12.0) / 18.0)
    score *= max(0.2, 1.0 - min(speed_jump_kmh, 12.0) / 16.0)
    score *= max(0.25, 1.0 - _id_switch_risk(track))
    score *= max(0.4, contact_quality_score)
    if speed > 18.0:
        score *= 0.2
    return float(max(0.0, min(1.0, score)))


def _id_switch_risk(track: dict[str, Any]) -> float:
    explicit = _optional_float(track.get("id_switch_risk"))
    if explicit is not None:
        return max(0.0, min(1.0, explicit))
    risk = 0.0
    if track.get("tracklet_relinked"):
        risk = max(risk, 0.45)
    if track.get("association_rejection_reason") or track.get("integrity_rejection_reason"):
        risk = max(risk, 0.7)
    return risk


def _speed_source(track: dict[str, Any]) -> str | None:
    source = track.get("speed_source")
    if source:
        return str(source)
    if track.get("speed_kmh") is None:
        return None
    if track.get("fixed_lag_backfilled") or track.get("reconstructed"):
        return "fixed_lag_rts_backfill"
    if track.get("imm_speed_kmh") is not None:
        return "imm_world_velocity"
    return str(track.get("measurement_source") or track.get("contact_source") or "world_velocity")


def _contact_quality_label(track: dict[str, Any], contact_quality_score: float) -> str:
    state = str(track.get("contact_state") or "").lower()
    policy = str(track.get("measurement_policy") or "").lower()
    if policy == "reject" or track.get("contact_outlier_source"):
        return "polluted"
    if "swing" in state or "toeoff" in state:
        return "swing"
    if "stance" in state or "support" in state or "double" in state:
        return "stance"
    if contact_quality_score >= 0.72:
        return "stance"
    if contact_quality_score <= 0.3:
        return "polluted"
    return "unknown"


def _speed_quality_label(track: dict[str, Any], speed_jump_kmh: float) -> str:
    speed = _optional_float(track.get("speed_kmh"))
    if speed is None:
        return "rejected"
    if speed > 18.0 or not bool(track.get("physics_valid", False)):
        return "rejected"
    if bool(track.get("rejection_reason")):
        return "uncertain"
    uncertainty = _optional_float(track.get("speed_uncertainty_kmh"))
    id_risk = _id_switch_risk(track)
    uncertainty_gate = max(8.0, speed * 0.75)
    jump_gate = max(6.0, speed * 1.5)
    if (
        id_risk < 0.65
        and (uncertainty is None or uncertainty <= uncertainty_gate)
        and speed_jump_kmh <= jump_gate
    ):
        return "valid"
    return "uncertain"


def _id_continuity_label(track: dict[str, Any], frame_indices: list[int]) -> str:
    if _id_switch_risk(track) >= 0.65:
        return "switch_risk"
    ordered = sorted(set(frame_indices))
    if any(curr - prev > 1 for prev, curr in zip(ordered, ordered[1:], strict=False)):
        return "fragmented"
    return "continuous"


def _feature_value(row: PseudoLabelRow, name: str) -> float:
    value = getattr(row, name)
    if value is None or isinstance(value, bool):
        return 0.0
    return float(value)


def _summarize_rows(rows: list[PseudoLabelRow]) -> dict[str, Any]:
    covered = [
        row
        for row in rows
        if row.speed_kmh is not None and row.speed_quality_label != "rejected"
    ]
    speeds = [float(row.speed_kmh) for row in covered if row.speed_kmh is not None]
    jumps = [row.speed_jump_kmh for row in rows]
    return {
        "rows": len(rows),
        "person_speed_coverage": len(covered) / len(rows) if rows else 0.0,
        "max_pedestrian_speed_kmh": max(speeds) if speeds else None,
        "avg_speed_kmh": mean(speeds) if speeds else None,
        "speed_jump_p95_kmh": _percentile(jumps, 95.0),
        "speed_quality_counts": _counts(row.speed_quality_label for row in rows),
        "contact_quality_counts": _counts(row.contact_quality_label for row in rows),
        "id_continuity_counts": _counts(row.id_continuity_label for row in rows),
    }


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    return float(np.percentile(np.asarray(values, dtype=np.float64), percentile))


def _counts(values: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[str(value)] = counts.get(str(value), 0) + 1
    return counts


def _manifest_item_dict(item: PedestrianClipManifestItem) -> dict[str, Any]:
    value = asdict(item)
    value["tracker_variants"] = list(item.tracker_variants)
    return value


def _write_pseudo_labels(rows: list[PseudoLabelRow], output_dir: Path) -> tuple[Path, str]:
    try:
        import pyarrow as pa  # type: ignore[import-not-found]
        import pyarrow.parquet as pq  # type: ignore[import-not-found]
    except ImportError:
        path = output_dir / "pseudo_labels.jsonl"
        with path.open("w") as handle:
            for row in rows:
                handle.write(json.dumps(asdict(row)) + "\n")
        return path, "jsonl"
    path = output_dir / "pseudo_labels.parquet"
    table = pa.Table.from_pylist([asdict(row) for row in rows])
    pq.write_table(table, path)
    return path, "parquet"


def _write_manual_audit_samples(rows: list[PseudoLabelRow], path: Path) -> None:
    priority = sorted(
        rows,
        key=lambda row: (
            row.speed_quality_label == "valid",
            row.contact_quality_label == "stance",
            -row.id_switch_risk,
            -row.speed_jump_kmh,
        ),
    )[:250]
    fieldnames = [
        "clip",
        "frame_index",
        "tracker_id",
        "speed_kmh",
        "speed_quality_label",
        "contact_quality_label",
        "id_continuity_label",
        "id_switch_risk",
        "speed_jump_kmh",
        "speed_source",
    ]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in priority:
            writer.writerow({name: getattr(row, name) for name in fieldnames})
