from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def load_optional_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return load_json(path)


def _build_tuning_summary(tuning_dir: Path | None) -> dict[str, Any] | None:
    if tuning_dir is None:
        return None
    tuning = load_optional_json(tuning_dir / "tuning_summary.json")
    if tuning is None:
        return None
    best = tuning.get("best_trial") or {}
    return {
        "clip": tuning.get("clip"),
        "trial_count": tuning.get("trial_count", 0),
        "successful_trial_count": tuning.get("successful_trial_count", 0),
        "avg_tuning_score": tuning.get("avg_tuning_score"),
        "best_trial": {
            "confidence_threshold": best.get("confidence_threshold"),
            "frame_stride": best.get("frame_stride"),
            "max_frames": best.get("max_frames"),
            "quality_status": best.get("quality_status"),
            "quality_issues": best.get("quality_issues", []),
            "tuning_score": best.get("tuning_score"),
            "avg_speed_confidence": best.get("avg_speed_confidence"),
            "avg_speed_uncertainty_kmh": best.get("avg_speed_uncertainty_kmh"),
            "physical_quantity_score": best.get("physical_quantity_score"),
            "effective_processing_fps": best.get("effective_processing_fps"),
        },
        "report": str(tuning_dir / "tuning_report.md"),
    }


def _build_readiness_summary(readiness_dir: Path | None) -> dict[str, Any] | None:
    if readiness_dir is None:
        return None
    readiness = load_optional_json(readiness_dir / "demo_readiness.json")
    if readiness is None:
        return None
    return {
        "demo_readiness": readiness.get("demo_readiness"),
        "industrial_readiness": readiness.get("industrial_readiness"),
        "demo_issues": readiness.get("demo_issues", []),
        "industrial_issues": readiness.get("industrial_issues", []),
        "next_actions": readiness.get("next_actions", []),
        "report": str(readiness_dir / "demo_readiness.md"),
    }


def build_packet_summary(
    pipeline_dir: Path,
    tuning_dir: Path | None = None,
    readiness_dir: Path | None = None,
) -> dict[str, Any]:
    manifest = load_json(pipeline_dir / "pipeline_manifest.json")
    benchmark = load_json(Path(manifest["analysis"]) / "benchmark_summary.json")
    calibration = load_json(
        Path(manifest["calibration_validation"]) / "calibration_validation.json",
    )
    rows = benchmark.get("rows", [])
    primary_row = rows[0] if rows else None
    return {
        "pipeline_dir": str(pipeline_dir),
        "clips": manifest.get("clips") or [],
        "manual_calibration_count": manifest.get("manual_calibration_count", 0),
        "quality_counts": benchmark.get("quality_counts", {}),
        "primary_demo": {
            "clip": primary_row.get("clip") if primary_row else None,
            "quality_status": primary_row.get("quality_status") if primary_row else None,
            "quality_issues": primary_row.get("quality_issues") if primary_row else [],
            "recommendations": primary_row.get("recommendations") if primary_row else [],
            "avg_speed_confidence": (
                primary_row.get("avg_speed_confidence") if primary_row else None
            ),
            "avg_speed_uncertainty_kmh": (
                primary_row.get("avg_speed_uncertainty_kmh") if primary_row else None
            ),
            "physical_quantity_score": (
                primary_row.get("physical_quantity_score") if primary_row else None
            ),
        },
        "artifacts": {
            "calibration_preview_dir": str(
                Path(manifest["calibration_assets"]) / "calibration_previews",
            ),
            "calibration_template": str(
                Path(manifest["calibration_assets"]) / "video_calibration_templates.json",
            ),
            "calibration_validation": str(
                Path(manifest["calibration_validation"]) / "calibration_validation.md",
            ),
            "analysis_summary": str(Path(manifest["analysis"]) / "summary.json"),
            "benchmark_report": str(Path(manifest["analysis"]) / "benchmark_report.md"),
        },
        "calibration_validation": {
            "video_calibration_count": calibration.get("video_calibration_count", 0),
            "pass_count": calibration.get("pass_count", 0),
            "fail_count": calibration.get("fail_count", 0),
        },
        "tuning": _build_tuning_summary(tuning_dir),
        "readiness": _build_readiness_summary(readiness_dir),
    }


def render_readme(summary: dict[str, Any]) -> str:
    primary = summary["primary_demo"]
    lines = [
        "# Defense Packet",
        "",
        "## Readiness Gate",
        "",
    ]
    readiness = summary.get("readiness")
    if readiness is None:
        lines.extend(["No readiness gate report was attached.", ""])
    else:
        lines.extend(
            [
                f"- Demo readiness: `{readiness['demo_readiness']}`",
                f"- Industrial readiness: `{readiness['industrial_readiness']}`",
                f"- Demo issues: `{', '.join(readiness['demo_issues']) or 'none'}`",
                (
                    "- Industrial issues: "
                    f"`{', '.join(readiness['industrial_issues']) or 'none'}`"
                ),
                f"- Readiness report: `{readiness['report']}`",
                "",
            ],
        )
    lines.extend(
        [
            "## Primary Demo",
            "",
            f"- Clip: `{primary['clip']}`",
            f"- Quality status: `{primary['quality_status']}`",
            f"- Average speed confidence: `{primary['avg_speed_confidence']}`",
            f"- Average speed uncertainty: `{primary['avg_speed_uncertainty_kmh']} km/h`",
            f"- Physical quantity score: `{primary['physical_quantity_score']}`",
            f"- Issues: `{', '.join(primary['quality_issues']) or 'none'}`",
            "",
            "## Best Tuned Parameters",
            "",
        ],
    )
    tuning = summary.get("tuning")
    if tuning is None:
        lines.extend(
            [
                "No tuning summary was attached to this packet.",
                "",
            ],
        )
    else:
        best = tuning["best_trial"]
        lines.extend(
            [
                f"- Trials: `{tuning['successful_trial_count']}/{tuning['trial_count']}`",
                f"- Confidence: `{best['confidence_threshold']}`",
                f"- Frame stride: `{best['frame_stride']}`",
                f"- Max frames: `{best['max_frames']}`",
                f"- Quality: `{best['quality_status']}`",
                f"- Tuning score: `{best['tuning_score']}`",
                f"- Avg speed confidence: `{best['avg_speed_confidence']}`",
                f"- Avg speed uncertainty: `{best['avg_speed_uncertainty_kmh']} km/h`",
                f"- Physical quantity score: `{best['physical_quantity_score']}`",
                f"- Effective FPS: `{best['effective_processing_fps']}`",
                f"- Tuning report: `{tuning['report']}`",
                "",
            ],
        )
    lines.extend(
        [
            "## Required Next Step",
            "",
        ],
    )
    if summary["manual_calibration_count"] == 0:
        lines.extend(
            [
                "No per-video manual calibration preset is configured yet.",
                (
                    "Use the calibration preview image to correct P1-P4 pixel "
                    "coordinates, then copy the template into "
                    "`data/tests/calibration_presets.json`."
                ),
                "",
            ],
        )
    else:
        lines.append("Manual calibration presets are present. Re-run the pipeline after edits.")
        lines.append("")
    lines.extend(
        [
            "## Artifacts",
            "",
            f"- Calibration previews: `{summary['artifacts']['calibration_preview_dir']}`",
            f"- Calibration template: `{summary['artifacts']['calibration_template']}`",
            f"- Calibration validation: `{summary['artifacts']['calibration_validation']}`",
            f"- Analysis summary: `{summary['artifacts']['analysis_summary']}`",
            f"- Benchmark report: `{summary['artifacts']['benchmark_report']}`",
            "",
            "## Recommendations",
            "",
        ],
    )
    for recommendation in primary["recommendations"]:
        lines.append(f"- {recommendation}")
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a compact defense packet from pipeline output.",
    )
    parser.add_argument("--pipeline-dir", default="data/outputs/main_demo_pipeline")
    parser.add_argument("--tuning-dir", default="data/outputs/main_demo_tuning")
    parser.add_argument("--readiness-dir", default="data/outputs/demo_readiness")
    parser.add_argument("--output-dir", default="data/outputs/defense_packet")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = build_packet_summary(
        Path(args.pipeline_dir),
        Path(args.tuning_dir),
        Path(args.readiness_dir),
    )
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "defense_packet_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
    )
    (output_dir / "README.md").write_text(render_readme(summary))
    print(json.dumps({"output_dir": str(output_dir)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
