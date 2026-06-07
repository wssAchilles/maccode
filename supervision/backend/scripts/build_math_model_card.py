from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _speed_tracks(report: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        track
        for track in report.get("active_tracks", [])
        if track.get("speed_kmh") is not None and track.get("physics_valid", True)
    ]


def build_model_card(analysis_path: Path, readiness_path: Path | None = None) -> dict[str, Any]:
    analysis = load_json(analysis_path)
    report = analysis["final_report"]
    tracks = _speed_tracks(report)
    uncertainties = [
        track["speed_uncertainty_kmh"]
        for track in tracks
        if track.get("speed_uncertainty_kmh") is not None
    ]
    confidences = [
        track["speed_confidence"]
        for track in tracks
        if track.get("speed_confidence") is not None
    ]
    readiness = load_json(readiness_path) if readiness_path and readiness_path.exists() else None
    return {
        "clip": analysis["clip"],
        "model_chain": [
            "YOLO semantic detection",
            "supervision ByteTrack identity preservation",
            "RANSAC homography pixel-to-ground projection",
            "class-routed constant-velocity Kalman filtering",
            "speed uncertainty propagation",
            "joint_speed_uncertainty_posterior_v1",
            "nis_consistency_diagnostics_v1",
            "synthetic_speed_parameter_sweep_v1",
            "Greenshields traffic-flow interpretation",
            "trajectory-geometry safety surrogate",
            "LLM context assembly",
        ],
        "geometry_model": {
            "formula": "s [u, v, 1]^T = H [X, Y, 1]^T",
            "calibration_source": analysis["calibration"]["source"],
            "calibration_trusted": analysis["calibration"].get("trusted"),
            "calibration_quality": analysis["calibration"]["quality"],
            "pixel_to_world_rmse_m": analysis["calibration"].get(
                "pixel_to_world_rmse_m",
                analysis["calibration"]["rmse"],
            ),
            "world_to_pixel_rmse_px": analysis["calibration"].get(
                "world_to_pixel_rmse_px",
            ),
            "validation_max_error_px": analysis["calibration"].get(
                "validation_max_error_px",
            ),
            "inlier_count": analysis["calibration"]["inlier_count"],
            "position_rmse_floor_m": analysis["calibration"]["position_rmse_floor_m"],
            "scale_uncertainty_pct": analysis["calibration"]["scale_uncertainty_pct"],
        },
        "kinematics_model": {
            "state_vector": "[x, y, vx, vy]",
            "speed_formula": "speed_kmh = 3.6 * sqrt(vx^2 + vy^2)",
            "speed_track_count": len(tracks),
            "avg_speed_confidence": mean(confidences) if confidences else None,
            "avg_speed_uncertainty_kmh": mean(uncertainties) if uncertainties else None,
            "sample_tracks": tracks[:3],
        },
        "uncertainty_model": {
            "scale_uncertainty_pct": analysis["sensitivity"]["scale_uncertainty_pct"],
            "speed_band_kmh": analysis["sensitivity"]["speed_band_kmh"],
            "space_mean_speed_band_kmh": analysis["sensitivity"][
                "space_mean_speed_band_kmh"
            ],
            "interpretation": analysis["sensitivity"]["interpretation"],
        },
        "traffic_flow_model": report.get("traffic_flow"),
        "safety_model": report.get("safety_metrics"),
        "readiness": readiness,
    }


def _fmt(value: object, suffix: str = "") -> str:
    if value is None:
        return "N/A"
    if isinstance(value, float):
        return f"{value:.3f}{suffix}"
    return f"{value}{suffix}"


def render_markdown(card: dict[str, Any]) -> str:
    geometry = card["geometry_model"]
    kinematics = card["kinematics_model"]
    uncertainty = card["uncertainty_model"]
    flow = card["traffic_flow_model"] or {}
    safety = card["safety_model"] or {}
    readiness = card.get("readiness") or {}
    lines = [
        "# Math Model Card",
        "",
        f"- Clip: `{card['clip']}`",
        f"- Demo readiness: `{readiness.get('demo_readiness', 'N/A')}`",
        f"- Industrial readiness: `{readiness.get('industrial_readiness', 'N/A')}`",
        "",
        "## Model Chain",
        "",
    ]
    for step in card["model_chain"]:
        lines.append(f"- {step}")
    lines.extend(
        [
            "",
            "## Geometry Model",
            "",
            f"- Formula: `{geometry['formula']}`",
            f"- Calibration source: `{geometry['calibration_source']}`",
            f"- Calibration trusted: `{geometry['calibration_trusted']}`",
            f"- Calibration quality: `{geometry['calibration_quality']}`",
            f"- Inliers: `{geometry['inlier_count']}`",
            f"- Pixel->world RMSE: `{_fmt(geometry['pixel_to_world_rmse_m'], ' m')}`",
            f"- World->pixel RMSE: `{_fmt(geometry['world_to_pixel_rmse_px'], ' px')}`",
            f"- Validation max error: `{_fmt(geometry['validation_max_error_px'], ' px')}`",
            f"- Position RMSE floor: `{_fmt(geometry['position_rmse_floor_m'], ' m')}`",
            f"- Scale uncertainty: `{_fmt(geometry['scale_uncertainty_pct'], '%')}`",
            "",
            "## Kinematics Model",
            "",
            f"- State vector: `{kinematics['state_vector']}`",
            f"- Speed formula: `{kinematics['speed_formula']}`",
            f"- Speed tracks: `{kinematics['speed_track_count']}`",
            f"- Avg confidence: `{_fmt(kinematics['avg_speed_confidence'])}`",
            f"- Avg uncertainty: `{_fmt(kinematics['avg_speed_uncertainty_kmh'], ' km/h')}`",
            "",
            "## Uncertainty Propagation",
            "",
            f"- Speed band: `{uncertainty['speed_band_kmh']}`",
            f"- Space mean speed band: `{uncertainty['space_mean_speed_band_kmh']}`",
            f"- Interpretation: {uncertainty['interpretation']}",
            "",
            "## Traffic Flow",
            "",
            f"- Flow q: `{_fmt(flow.get('flow_q_veh_per_hour'), ' veh/h')}`",
            f"- Density k: `{_fmt(flow.get('density_k_veh_per_km'), ' veh/km')}`",
            f"- Space mean speed: `{_fmt(flow.get('space_mean_speed_kmh'), ' km/h')}`",
            f"- Congestion level: `{flow.get('congestion_level', 'N/A')}`",
            f"- Greenshields speed: `{_fmt(flow.get('greenshields_speed_kmh'), ' km/h')}`",
            "",
            "## Safety Surrogate",
            "",
            f"- Vehicle pairs: `{safety.get('vehicle_pair_count', 'N/A')}`",
            f"- Min headway: `{_fmt(safety.get('min_time_headway_sec'), ' s')}`",
            f"- Min TTC: `{_fmt(safety.get('min_time_to_collision_sec'), ' s')}`",
            f"- Risk level: `{safety.get('risk_level', 'N/A')}`",
            "",
            "## Track Samples",
            "",
            "| Track | Class | Speed | CI | Ground XY | Heading | Accel |",
            "| ---: | --- | ---: | --- | --- | ---: | ---: |",
        ],
    )
    for track in kinematics["sample_tracks"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(track["tracker_id"]),
                    str(track["class_name"]),
                    _fmt(track.get("speed_kmh"), " km/h"),
                    str(track.get("speed_confidence_interval_kmh")),
                    (
                        f"({_fmt(track.get('ground_x_m'))}, "
                        f"{_fmt(track.get('ground_y_m'))})"
                    ),
                    _fmt(track.get("heading_deg")),
                    _fmt(track.get("acceleration_mps2")),
                ],
            )
            + " |",
        )
    lines.extend(
        [
            "",
            "## Defense Boundary",
            "",
            (
                "This card proves the implemented mathematical chain on real video. "
                "Absolute speed and Homography Grid claims remain suppressed until "
                "`calibration_trusted=true` with independent validation error under "
                "the configured pixel gate."
            ),
        ],
    )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a defense math model card.")
    parser.add_argument(
        "--analysis",
        default="data/outputs/main_demo_pipeline/analysis/028_red_light_static_0008s_30s.json",
    )
    parser.add_argument(
        "--readiness",
        default="data/outputs/demo_readiness/demo_readiness.json",
    )
    parser.add_argument("--output-dir", default="data/outputs/math_model_card")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    card = build_model_card(Path(args.analysis), Path(args.readiness))
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "math_model_card.json").write_text(
        json.dumps(card, ensure_ascii=False, indent=2),
    )
    (output_dir / "math_model_card.md").write_text(render_markdown(card))
    print(json.dumps({"output_dir": str(output_dir), "clip": card["clip"]}, indent=2))


if __name__ == "__main__":
    main()
