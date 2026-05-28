from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _quality_rank(status: str | None) -> int:
    return {"fail": 0, "warn": 1, "pass": 2}.get(status or "fail", 0)


def build_readiness_report(
    pipeline_dir: Path,
    tuning_dir: Path,
) -> dict[str, Any]:
    manifest = load_json(pipeline_dir / "pipeline_manifest.json")
    benchmark = load_json(Path(manifest["analysis"]) / "benchmark_summary.json")
    calibration = load_json(
        Path(manifest["calibration_validation"]) / "calibration_validation.json",
    )
    tuning = load_json(tuning_dir / "tuning_summary.json")
    row = benchmark["rows"][0] if benchmark.get("rows") else {}
    tuning_application = manifest.get("tuning_application") or {}
    issues: list[str] = []

    if not tuning_application.get("applied"):
        issues.append("tuning_not_applied_to_pipeline")
    if _quality_rank(row.get("quality_status")) < _quality_rank("warn"):
        issues.append("demo_quality_below_warn")
    if (row.get("physical_quantity_score") or 0.0) < 1.0:
        issues.append("physical_quantity_coverage_incomplete")
    if (row.get("avg_speed_confidence") or 0.0) < 0.75:
        issues.append("speed_confidence_below_demo_threshold")
    if row.get("avg_speed_uncertainty_kmh") is None:
        issues.append("speed_uncertainty_missing")
    elif row["avg_speed_uncertainty_kmh"] > 8.0:
        issues.append("speed_uncertainty_above_demo_threshold")
    if benchmark.get("quality_counts", {}).get("fail", 0) > 0:
        issues.append("benchmark_contains_failed_clip")

    demo_status = "ready" if not issues else "not_ready"
    industrial_issues = list(calibration.get("readiness_issues", []))
    if row.get("calibration_source") != "video_manual_preset":
        industrial_issues.append("calibration_source_not_video_manual_preset")
    industrial_status = "ready" if not industrial_issues else "not_ready"

    return {
        "pipeline_dir": str(pipeline_dir),
        "tuning_dir": str(tuning_dir),
        "clip": row.get("clip"),
        "demo_readiness": demo_status,
        "demo_issues": issues,
        "industrial_readiness": industrial_status,
        "industrial_issues": sorted(set(industrial_issues)),
        "metrics": {
            "quality_status": row.get("quality_status"),
            "quality_issues": row.get("quality_issues", []),
            "avg_speed_confidence": row.get("avg_speed_confidence"),
            "avg_speed_uncertainty_kmh": row.get("avg_speed_uncertainty_kmh"),
            "physical_quantity_score": row.get("physical_quantity_score"),
            "effective_processing_fps": row.get("effective_processing_fps"),
            "calibration_source": row.get("calibration_source"),
            "tuning_applied": tuning_application.get("applied", False),
            "tuning_score": tuning.get("best_trial", {}).get("tuning_score"),
        },
        "next_actions": _next_actions(demo_status, industrial_status),
    }


def _next_actions(demo_status: str, industrial_status: str) -> list[str]:
    actions: list[str] = []
    if demo_status != "ready":
        actions.append("rerun parameter tuning and pipeline before using the main demo")
    if industrial_status != "ready":
        actions.append("add per-video manual ground-control points and rerun validation")
    if not actions:
        actions.append("ready for defense demo and calibrated speed discussion")
    return actions


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Demo Readiness Gate",
        "",
        f"- Clip: `{report['clip']}`",
        f"- Demo readiness: `{report['demo_readiness']}`",
        f"- Industrial readiness: `{report['industrial_readiness']}`",
        "",
        "## Metrics",
        "",
    ]
    for key, value in report["metrics"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Demo Issues", ""])
    if report["demo_issues"]:
        for issue in report["demo_issues"]:
            lines.append(f"- `{issue}`")
    else:
        lines.append("- none")
    lines.extend(["", "## Industrial Issues", ""])
    if report["industrial_issues"]:
        for issue in report["industrial_issues"]:
            lines.append(f"- `{issue}`")
    else:
        lines.append("- none")
    lines.extend(["", "## Next Actions", ""])
    for action in report["next_actions"]:
        lines.append(f"- {action}")
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check whether the real-video demo is ready for defense and industrial claims.",
    )
    parser.add_argument("--pipeline-dir", default="data/outputs/main_demo_pipeline")
    parser.add_argument("--tuning-dir", default="data/outputs/main_demo_tuning")
    parser.add_argument("--output-dir", default="data/outputs/demo_readiness")
    parser.add_argument(
        "--strict-industrial",
        action="store_true",
        help="Exit nonzero unless industrial readiness is also ready.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_readiness_report(Path(args.pipeline_dir), Path(args.tuning_dir))
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "demo_readiness.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
    )
    (output_dir / "demo_readiness.md").write_text(render_markdown(report))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["demo_readiness"] != "ready":
        sys.exit(1)
    if args.strict_industrial and report["industrial_readiness"] != "ready":
        sys.exit(1)


if __name__ == "__main__":
    main()
