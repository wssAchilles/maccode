from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from statistics import mean
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _fmt(value: object, suffix: str = "") -> str:
    if value is None:
        return "N/A"
    if isinstance(value, float):
        return f"{value:.2f}{suffix}"
    return f"{value}{suffix}"


def _successful_results(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [result for result in payload.get("results", []) if result.get("status") == "ok"]


def _numeric_track_values(tracks: list[dict[str, Any]], key: str) -> list[float]:
    values: list[float] = []
    for track in tracks:
        value = track.get(key)
        if isinstance(value, int | float):
            values.append(float(value))
    return values


def _p95(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(round((len(ordered) - 1) * 0.95)))
    return float(ordered[index])


def _ratio_diagnostic(
    primary: dict[str, Any],
    fallback: dict[str, Any],
    key: str,
) -> float | None:
    for source in (primary, fallback):
        value = source.get(key)
        if isinstance(value, int | float):
            return float(value)
    return None


def _int_diagnostic(
    primary: dict[str, Any],
    fallback: dict[str, Any],
    key: str,
) -> int:
    value = _ratio_diagnostic(primary, fallback, key)
    return int(value or 0)


def grade_row(row: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    recommendations: list[str] = []
    if row["calibration_source"] != "video_manual_preset":
        issues.append("demo_calibration")
        recommendations.append(
            "treat speeds as weak-scale estimates and strengthen automatic geometry priors",
        )
    if row["speed_tracks"] == 0:
        issues.append("no_speed_tracks")
        recommendations.append(
            "increase max_frames or reduce frame_stride for longer track history",
        )
    confidence = row["avg_speed_confidence"]
    if confidence is not None and confidence < 0.45:
        issues.append("low_speed_confidence")
        recommendations.append(
            "process a longer temporal window and down-rank weak geometry tracks",
        )
    uncertainty = row["avg_speed_uncertainty_kmh"]
    if uncertainty is not None and uncertainty > 15.0:
        issues.append("high_speed_uncertainty")
        recommendations.append(
            "use automatic geometry priors, contact gating, and longer tracks "
            "to narrow uncertainty",
        )
    if row["effective_processing_fps"] < 5.0:
        issues.append("slow_processing")
        recommendations.append("use MPS when available or increase frame_stride for demo runs")

    if not issues:
        status = "pass"
    elif set(issues) <= {"demo_calibration"}:
        status = "warn"
    else:
        status = "fail"
    return {
        "quality_status": status,
        "quality_issues": issues,
        "recommendations": recommendations,
    }


def _has_numeric(track: dict[str, Any], key: str) -> bool:
    value = track.get(key)
    return isinstance(value, int | float)


def build_physical_quantity_coverage(
    report: dict[str, Any],
    speed_tracks: list[dict[str, Any]],
) -> dict[str, Any]:
    active_tracks = report.get("active_tracks", [])
    traffic_flow = report.get("traffic_flow") or {}
    people_count = report.get("regional_people_count") or {}
    infrastructure = report.get("infrastructure_semantics") or {}
    safety = report.get("safety_metrics") or {}

    ground_position_tracks = [
        track
        for track in active_tracks
        if _has_numeric(track, "ground_x_m") and _has_numeric(track, "ground_y_m")
    ]
    velocity_vector_tracks = [
        track
        for track in speed_tracks
        if _has_numeric(track, "velocity_x_mps") and _has_numeric(track, "velocity_y_mps")
    ]
    acceleration_tracks = [
        track for track in speed_tracks if _has_numeric(track, "acceleration_mps2")
    ]
    heading_tracks = [track for track in speed_tracks if _has_numeric(track, "heading_deg")]
    confidence_interval_tracks = [
        track
        for track in speed_tracks
        if isinstance(track.get("speed_confidence_interval_kmh"), list)
        and len(track["speed_confidence_interval_kmh"]) == 2
    ]
    uncertainty_tracks = [
        track for track in speed_tracks if _has_numeric(track, "speed_uncertainty_kmh")
    ]
    traffic_flow_available = all(
        traffic_flow.get(key) is not None
        for key in [
            "flow_q_veh_per_hour",
            "density_k_veh_per_km",
            "space_mean_speed_kmh",
            "congestion_level",
        ]
    )
    safety_available = all(
        key in safety
        for key in ["risk_level", "min_time_to_collision_sec", "min_time_headway_sec"]
    )

    return {
        "micro_kinematics": {
            "active_track_count": len(active_tracks),
            "speed_track_count": len(speed_tracks),
            "ground_position_track_count": len(ground_position_tracks),
            "velocity_vector_track_count": len(velocity_vector_tracks),
            "acceleration_track_count": len(acceleration_tracks),
            "heading_track_count": len(heading_tracks),
            "confidence_interval_track_count": len(confidence_interval_tracks),
            "uncertainty_track_count": len(uncertainty_tracks),
            "has_instantaneous_speed": len(speed_tracks) > 0,
            "has_ground_coordinates": len(ground_position_tracks) > 0,
            "has_speed_confidence_interval": len(confidence_interval_tracks) > 0,
        },
        "macro_statistics": {
            "people_count": people_count.get("people_count", 0),
            "has_regional_people_count": people_count.get("people_count") is not None,
            "has_traffic_flow": traffic_flow_available,
            "traffic_flow_keys": {
                "flow_q_veh_per_hour": traffic_flow.get("flow_q_veh_per_hour"),
                "density_k_veh_per_km": traffic_flow.get("density_k_veh_per_km"),
                "space_mean_speed_kmh": traffic_flow.get("space_mean_speed_kmh"),
                "congestion_level": traffic_flow.get("congestion_level"),
            },
        },
        "environment_semantics": {
            "traffic_light_count": infrastructure.get("traffic_light_count", 0),
            "static_context_count": len(infrastructure.get("static_context", [])),
            "has_infrastructure_state": infrastructure.get("traffic_light_count", 0) > 0
            or len(infrastructure.get("static_context", [])) > 0,
            "has_safety_metrics": safety_available,
            "risk_level": safety.get("risk_level"),
        },
    }


def coverage_score(coverage: dict[str, Any]) -> float:
    checks = [
        coverage["micro_kinematics"]["has_instantaneous_speed"],
        coverage["micro_kinematics"]["has_ground_coordinates"],
        coverage["micro_kinematics"]["has_speed_confidence_interval"],
        coverage["macro_statistics"]["has_regional_people_count"],
        coverage["macro_statistics"]["has_traffic_flow"],
        coverage["environment_semantics"]["has_infrastructure_state"],
        coverage["environment_semantics"]["has_safety_metrics"],
    ]
    return sum(1 for check in checks if check) / len(checks)


def build_benchmark_summary(payload: dict[str, Any]) -> dict[str, Any]:
    results = _successful_results(payload)
    rows: list[dict[str, Any]] = []
    all_track_confidences: list[float] = []
    all_speed_uncertainties: list[float] = []
    for result in results:
        report = result["final_report"]
        tracks = report.get("active_tracks", [])
        speed_tracks = [
            track
            for track in tracks
            if track.get("speed_kmh") is not None and track.get("physics_valid", True)
        ]
        confidences = [
            track["speed_confidence"]
            for track in speed_tracks
            if track.get("speed_confidence") is not None
        ]
        uncertainties = [
            track["speed_uncertainty_kmh"]
            for track in speed_tracks
            if track.get("speed_uncertainty_kmh") is not None
        ]
        trajectory_diagnostics = report.get("trajectory_diagnostics") or {}
        integrity_diagnostics = report.get("integrity_diagnostics") or {}
        calibration_diagnostics = report.get("calibration_diagnostics") or {}
        speed_jump_values = _numeric_track_values(speed_tracks, "speed_jump_p95_kmh")
        acceleration_values = _numeric_track_values(speed_tracks, "acceleration_p95_mps2")
        jerk_values = _numeric_track_values(speed_tracks, "jerk_p95_mps3")
        all_track_confidences.extend(confidences)
        all_speed_uncertainties.extend(uncertainties)
        coverage = build_physical_quantity_coverage(report, speed_tracks)
        row = {
            "clip": result["clip"],
            "profile": result["scene_profile"]["name"],
            "calibration_source": result["calibration"]["source"],
            "calibration_quality": result["calibration"]["quality"],
            "rmse_floor_m": result["calibration"]["position_rmse_floor_m"],
            "scale_uncertainty_pct": result["calibration"]["scale_uncertainty_pct"],
            "active_tracks": len(tracks),
            "speed_tracks": len(speed_tracks),
            "people_count": report["regional_people_count"]["people_count"],
            "traffic_light_count": report["infrastructure_semantics"]["traffic_light_count"],
            "mean_speed_kmh": report["traffic_flow"]["space_mean_speed_kmh"],
            "mean_speed_band_kmh": result["sensitivity"]["space_mean_speed_band_kmh"],
            "avg_speed_confidence": mean(confidences) if confidences else None,
            "avg_speed_uncertainty_kmh": mean(uncertainties) if uncertainties else None,
            "congestion_level": report["traffic_flow"]["congestion_level"],
            "risk_level": report["safety_metrics"]["risk_level"],
            "effective_processing_fps": result["effective_processing_fps"],
            "speed_jump_p95_kmh": _p95(speed_jump_values),
            "acceleration_p95_mps2": _p95(acceleration_values),
            "jerk_p95_mps3": _p95(jerk_values),
            "id_switch_risk_count": _int_diagnostic(
                trajectory_diagnostics,
                integrity_diagnostics,
                "id_switch_risk_count",
            ),
            "association_match_count": _int_diagnostic(
                trajectory_diagnostics,
                integrity_diagnostics,
                "association_match_count",
            ),
            "low_score_recovery_count": _int_diagnostic(
                trajectory_diagnostics,
                integrity_diagnostics,
                "low_score_recovery_count",
            ),
            "fragmentation_count": _int_diagnostic(
                trajectory_diagnostics,
                integrity_diagnostics,
                "fragmentation_count",
            ),
            "speed_frozen_ratio": _ratio_diagnostic(
                trajectory_diagnostics,
                integrity_diagnostics,
                "speed_frozen_ratio",
            ),
            "bev_rejected_ratio": _ratio_diagnostic(
                trajectory_diagnostics,
                integrity_diagnostics,
                "bev_rejected_ratio",
            ),
            "contact_fusion_low_confidence_ratio": _ratio_diagnostic(
                trajectory_diagnostics,
                integrity_diagnostics,
                "contact_fusion_low_confidence_ratio",
            ),
            "contact_outlier_ratio": _ratio_diagnostic(
                trajectory_diagnostics,
                integrity_diagnostics,
                "contact_outlier_ratio",
            ),
            "optical_flow_low_inlier_ratio": _ratio_diagnostic(
                trajectory_diagnostics,
                integrity_diagnostics,
                "optical_flow_low_inlier_ratio",
            ),
            "weak_scale_track_count": sum(
                1
                for track in speed_tracks
                if track.get("scale_confidence_label") == "weak_scale"
            ),
            "weak_scale_mode": bool(
                calibration_diagnostics.get("weak_scale_mode")
                or integrity_diagnostics.get("weak_scale_mode")
            ),
            "calibration_candidate_score": calibration_diagnostics.get(
                "calibration_candidate_score"
            ),
            "physical_quantity_coverage": coverage,
            "physical_quantity_score": coverage_score(coverage),
        }
        row.update(grade_row(row))
        rows.append(row)

    return {
        "total_successful_clips": len(results),
        "avg_track_speed_confidence": (
            mean(all_track_confidences) if all_track_confidences else None
        ),
        "avg_speed_uncertainty_kmh": (
            mean(all_speed_uncertainties) if all_speed_uncertainties else None
        ),
        "mps_available": payload.get("summary", {}).get("mps_available"),
        "mps_built": payload.get("summary", {}).get("mps_built"),
        "quality_counts": {
            status: sum(1 for row in rows if row["quality_status"] == status)
            for status in ["pass", "warn", "fail"]
        },
        "avg_physical_quantity_score": (
            mean(row["physical_quantity_score"] for row in rows) if rows else None
        ),
        "vehicle_speed_aggregate": payload.get("summary", {}).get(
            "vehicle_speed_aggregate",
            {},
        ),
        "rows": rows,
    }


def render_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Real Video Benchmark Report",
        "",
        "This report is generated from a real video analysis summary JSON file.",
        "",
        "## Aggregate",
        "",
        f"- Successful clips: {summary['total_successful_clips']}",
        f"- Average track speed confidence: {_fmt(summary['avg_track_speed_confidence'])}",
        f"- Average speed uncertainty: {_fmt(summary['avg_speed_uncertainty_kmh'], ' km/h')}",
        f"- MPS built: {summary['mps_built']}",
        f"- MPS available in this run: {summary['mps_available']}",
        f"- Quality pass/warn/fail: {summary['quality_counts']}",
        f"- Average physical quantity score: {_fmt(summary.get('avg_physical_quantity_score'))}",
        "",
    ]
    vehicle_aggregate = summary.get("vehicle_speed_aggregate") or {}
    if vehicle_aggregate:
        lines.extend(
            [
                "## Vehicle Speed Aggregate",
                "",
                f"- Vehicle samples: {vehicle_aggregate.get('vehicle_track_samples', 0)}",
                (
                    "- Displayable vehicle samples: "
                    f"{vehicle_aggregate.get('displayable_vehicle_track_samples', 0)}"
                ),
                (
                    "- Vehicle display coverage: "
                    f"{_fmt(vehicle_aggregate.get('vehicle_display_coverage'))}"
                ),
                (
                    "- Dense-city acceptance: "
                    f"{vehicle_aggregate.get('passes_dense_city_acceptance')}"
                ),
                f"- N/A by reason: {vehicle_aggregate.get('na_by_reason', {})}",
                "",
            ],
        )
    lines.extend(
        [
            "## Scene Rows",
            "",
            "| Clip | Profile | Calib | Tracks | Speed tracks | Mean speed band | "
            "Avg confidence | Avg uncertainty | Physics | People | Lights | "
            "Congestion | Risk | FPS | Quality |",
            (
                "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: "
                "| ---: | --- | --- | ---: | --- |"
            ),
        ],
    )
    for row in summary["rows"]:
        band = row["mean_speed_band_kmh"]
        speed_band = (
            "N/A"
            if band[0] is None or band[1] is None
            else f"{band[0]:.2f}-{band[1]:.2f} km/h"
        )
        lines.append(
            "| "
            + " | ".join(
                [
                    row["clip"],
                    row["profile"],
                    row["calibration_source"],
                    str(row["active_tracks"]),
                    str(row["speed_tracks"]),
                    speed_band,
                    _fmt(row["avg_speed_confidence"]),
                    _fmt(row["avg_speed_uncertainty_kmh"], " km/h"),
                    _fmt(row["physical_quantity_score"]),
                    str(row["people_count"]),
                    str(row["traffic_light_count"]),
                    row["congestion_level"],
                    row["risk_level"],
                    _fmt(row["effective_processing_fps"]),
                    row["quality_status"],
                ],
            )
            + " |",
        )
    lines.extend(
        [
            "",
            "## Precision Diagnostics",
            "",
            "| Clip | Speed jump p95 | Accel p95 | Jerk p95 | ID switch risks | "
            "Assoc matches | Low-score recoveries | Fragmentation | "
            "Frozen ratio | BEV rejected | Contact low conf | Contact outliers | "
            "Flow low inliers | Weak-scale tracks | Calib candidate score |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | "
            "---: | ---: | ---: | ---: | ---: | ---: |",
        ],
    )
    for row in summary["rows"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    row["clip"],
                    _fmt(row.get("speed_jump_p95_kmh"), " km/h"),
                    _fmt(row.get("acceleration_p95_mps2"), " m/s2"),
                    _fmt(row.get("jerk_p95_mps3"), " m/s3"),
                    str(row.get("id_switch_risk_count", 0)),
                    str(row.get("association_match_count", 0)),
                    str(row.get("low_score_recovery_count", 0)),
                    str(row.get("fragmentation_count", 0)),
                    _fmt(row.get("speed_frozen_ratio")),
                    _fmt(row.get("bev_rejected_ratio")),
                    _fmt(row.get("contact_fusion_low_confidence_ratio")),
                    _fmt(row.get("contact_outlier_ratio")),
                    _fmt(row.get("optical_flow_low_inlier_ratio")),
                    str(row.get("weak_scale_track_count", 0)),
                    _fmt(row.get("calibration_candidate_score")),
                ],
            )
            + " |",
        )
    lines.extend(["", "## Quality Gates", ""])
    for row in summary["rows"]:
        if not row["quality_issues"]:
            continue
        lines.append(f"### {row['clip']}")
        lines.append("")
        lines.append(f"- Status: {row['quality_status']}")
        lines.append(f"- Issues: {', '.join(row['quality_issues'])}")
        lines.append(f"- Recommendations: {'; '.join(row['recommendations'])}")
        lines.append("")
    lines.extend(
        [
            "",
            "## Physical Quantity Coverage",
            "",
            (
                "The benchmark audits whether each clip produced the semantic interface "
                "needed by the LLM agent: micro kinematics, macro traffic state, and "
                "environment/safety context."
            ),
            "",
            "| Clip | Speed | Ground XY | Speed CI | Traffic flow | People count | "
            "Infra state | Safety |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
        ],
    )
    for row in summary["rows"]:
        coverage = row["physical_quantity_coverage"]
        micro = coverage["micro_kinematics"]
        macro = coverage["macro_statistics"]
        environment = coverage["environment_semantics"]
        lines.append(
            "| "
            + " | ".join(
                [
                    row["clip"],
                    "yes" if micro["has_instantaneous_speed"] else "no",
                    "yes" if micro["has_ground_coordinates"] else "no",
                    "yes" if micro["has_speed_confidence_interval"] else "no",
                    "yes" if macro["has_traffic_flow"] else "no",
                    "yes" if macro["has_regional_people_count"] else "no",
                    "yes" if environment["has_infrastructure_state"] else "no",
                    "yes" if environment["has_safety_metrics"] else "no",
                ],
            )
            + " |",
        )
    lines.extend(
        [
            "## Interpretation",
            "",
            (
                "- `scene_profile_preset` proves the full mathematical chain but "
                "should be treated as demonstration-grade calibration."
            ),
            (
                "- `video_manual_preset` means surveyed or manually clicked "
                "ground-control points are being used for that clip."
            ),
            (
                "- A wide speed band or low confidence should be discussed as a "
                "calibration/noise limitation, not hidden."
            ),
            (
                "- MPS availability is recorded per run so defense claims do not "
                "overstate local acceleration."
            ),
        ],
    )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize real video analysis benchmark output.")
    parser.add_argument("--input", default="data/outputs/real_video_analysis/summary.json")
    parser.add_argument("--output-dir", default="data/outputs/real_video_analysis")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = json.loads(Path(args.input).read_text())
    summary = build_benchmark_summary(payload)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "benchmark_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
    )
    (output_dir / "benchmark_report.md").write_text(render_markdown(summary))
    print(json.dumps({"rows": len(summary["rows"]), "output_dir": str(output_dir)}, indent=2))


if __name__ == "__main__":
    main()
