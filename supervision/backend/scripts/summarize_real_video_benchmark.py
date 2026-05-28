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


def grade_row(row: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    recommendations: list[str] = []
    if row["calibration_source"] != "video_manual_preset":
        issues.append("demo_calibration")
        recommendations.append("replace scene profile with per-video ground-control points")
    if row["speed_tracks"] == 0:
        issues.append("no_speed_tracks")
        recommendations.append(
            "increase max_frames or reduce frame_stride for longer track history",
        )
    confidence = row["avg_speed_confidence"]
    if confidence is not None and confidence < 0.45:
        issues.append("low_speed_confidence")
        recommendations.append("tighten calibration points and process a longer temporal window")
    uncertainty = row["avg_speed_uncertainty_kmh"]
    if uncertainty is not None and uncertainty > 15.0:
        issues.append("high_speed_uncertainty")
        recommendations.append(
            "lower position_rmse_floor_m via manual calibration or longer tracks",
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


def build_benchmark_summary(payload: dict[str, Any]) -> dict[str, Any]:
    results = _successful_results(payload)
    rows: list[dict[str, Any]] = []
    all_track_confidences: list[float] = []
    all_speed_uncertainties: list[float] = []
    for result in results:
        report = result["final_report"]
        tracks = report.get("active_tracks", [])
        speed_tracks = [
            track for track in tracks if track.get("speed_kmh") is not None
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
        all_track_confidences.extend(confidences)
        all_speed_uncertainties.extend(uncertainties)
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
        "rows": rows,
    }


def render_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Real Video Benchmark Report",
        "",
        "This report is generated from `data/outputs/real_video_analysis/summary.json`.",
        "",
        "## Aggregate",
        "",
        f"- Successful clips: {summary['total_successful_clips']}",
        f"- Average track speed confidence: {_fmt(summary['avg_track_speed_confidence'])}",
        f"- Average speed uncertainty: {_fmt(summary['avg_speed_uncertainty_kmh'], ' km/h')}",
        f"- MPS built: {summary['mps_built']}",
        f"- MPS available in this run: {summary['mps_available']}",
        f"- Quality pass/warn/fail: {summary['quality_counts']}",
        "",
        "## Scene Rows",
        "",
        "| Clip | Profile | Calib | Tracks | Speed tracks | Mean speed band | "
        "Avg confidence | Avg uncertainty | People | Lights | Congestion | Risk | FPS | Quality |",
        (
            "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: "
            "| --- | --- | ---: | --- |"
        ),
    ]
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
