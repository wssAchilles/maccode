from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _load_reports(input_dir: Path) -> list[dict[str, Any]]:
    reports: list[dict[str, Any]] = []
    for path in sorted(input_dir.glob("*.json")):
        if path.name == "summary.json":
            continue
        payload = json.loads(path.read_text())
        final_report = payload.get("final_report")
        if isinstance(final_report, dict):
            reports.append({"clip": path.name, "final_report": final_report})
    return reports


def summarize(input_dir: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for item in _load_reports(input_dir):
        report = item["final_report"]
        benchmark = report.get("model_comparison_benchmark") or {}
        confidence = report.get("confidence_calibration_summary") or {}
        tracklet = report.get("tracklet_reassociation_summary") or {}
        calibration = report.get("calibration_sensitivity") or {}
        rows.append(
            {
                "clip": item["clip"],
                "baseline": benchmark.get("baseline"),
                "optimized": benchmark.get("optimized"),
                "gates": benchmark.get("gates"),
                "proxy_low_confidence_ratio": confidence.get(
                    "proxy_low_confidence_ratio"
                ),
                "tracklet_relinked_count": tracklet.get("relinked_count"),
                "speed_sensitivity_p95": calibration.get("speed_sensitivity_p95"),
            }
        )
    return {
        "clip_count": len(rows),
        "rows": rows,
        "model_reference": "phase3_model_comparison_summary",
    }


def render_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Phase 3 Model Comparison Benchmark",
        "",
        (
            "| Clip | Speed gate | Accel gate | Jerk gate | Low-conf proxy | "
            "Relinked | Calib sensitivity p95 |"
        ),
        "| --- | --- | --- | --- | ---: | ---: | ---: |",
    ]
    for row in summary["rows"]:
        gates = row.get("gates") or {}
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row["clip"]),
                    str(gates.get("speed_jump_p95_not_increased")),
                    str(gates.get("acceleration_p95_not_increased")),
                    str(gates.get("jerk_p95_not_increased")),
                    _fmt(row.get("proxy_low_confidence_ratio")),
                    _fmt(row.get("tracklet_relinked_count")),
                    _fmt(row.get("speed_sensitivity_p95")),
                ]
            )
            + " |"
        )
    return "\n".join(lines) + "\n"


def _fmt(value: object) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", default="data/real_video_outputs")
    parser.add_argument("--output-json")
    parser.add_argument("--output-md")
    args = parser.parse_args()
    summary = summarize(Path(args.input_dir))
    if args.output_json:
        Path(args.output_json).write_text(json.dumps(summary, indent=2))
    if args.output_md:
        Path(args.output_md).write_text(render_markdown(summary))
    if not args.output_json and not args.output_md:
        print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
