from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from statistics import mean
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/mpl")

from shared.configs.settings import Settings

from scripts.analyze_real_videos import (
    analyze_clip,
    load_calibration_presets,
    resolve_device,
)
from scripts.summarize_real_video_benchmark import build_benchmark_summary


def _split_grid(value: str) -> list[str]:
    items = [item.strip() for item in value.split(",") if item.strip()]
    if not items:
        raise ValueError("parameter grid cannot be empty")
    return items


def parse_float_grid(value: str) -> list[float]:
    return [float(item) for item in _split_grid(value)]


def parse_int_grid(value: str) -> list[int]:
    return [int(item) for item in _split_grid(value)]


def _clip_result_to_benchmark(result: dict[str, Any]) -> dict[str, Any]:
    benchmark = build_benchmark_summary({"summary": {}, "results": [result]})
    return benchmark["rows"][0] if benchmark["rows"] else {}


def tuning_score(row: dict[str, Any]) -> float:
    if not row:
        return 0.0
    quality_weight = {"pass": 1.0, "warn": 0.75, "fail": 0.35}
    quality = quality_weight.get(row["quality_status"], 0.0)
    confidence = row["avg_speed_confidence"] or 0.0
    physics = row.get("physical_quantity_score") or 0.0
    uncertainty = row["avg_speed_uncertainty_kmh"]
    uncertainty_score = 0.0 if uncertainty is None else max(0.0, 1.0 - uncertainty / 30.0)
    fps_score = min((row["effective_processing_fps"] or 0.0) / 12.0, 1.0)
    speed_track_score = min(row["speed_tracks"] / 4.0, 1.0)
    return (
        0.25 * quality
        + 0.20 * confidence
        + 0.20 * uncertainty_score
        + 0.15 * physics
        + 0.10 * fps_score
        + 0.10 * speed_track_score
    )


def run_tuning(args: argparse.Namespace) -> dict[str, Any]:
    settings = Settings()
    model_path = args.model or settings.cv.yolo_model
    device = resolve_device(args.device)
    presets = load_calibration_presets(Path(args.calibration_presets))
    clip_path = Path(args.input_dir) / args.clip
    confidences = parse_float_grid(args.confidences)
    frame_strides = parse_int_grid(args.frame_strides)
    max_frames_values = parse_int_grid(args.max_frames_values)

    rows: list[dict[str, Any]] = []
    for confidence in confidences:
        for frame_stride in frame_strides:
            for max_frames in max_frames_values:
                trial = {
                    "clip": args.clip,
                    "confidence_threshold": confidence,
                    "frame_stride": frame_stride,
                    "max_frames": max_frames,
                    "device": device,
                }
                try:
                    result = analyze_clip(
                        path=clip_path,
                        model_path=model_path,
                        device=device,
                        confidence=confidence,
                        frame_stride=frame_stride,
                        max_frames=max_frames,
                        presets=presets,
                    )
                    result["status"] = "ok"
                    benchmark_row = _clip_result_to_benchmark(result)
                    trial.update(
                        {
                            "status": "ok",
                            "quality_status": benchmark_row["quality_status"],
                            "quality_issues": benchmark_row["quality_issues"],
                            "active_tracks": benchmark_row["active_tracks"],
                            "speed_tracks": benchmark_row["speed_tracks"],
                            "avg_speed_confidence": benchmark_row["avg_speed_confidence"],
                            "avg_speed_uncertainty_kmh": benchmark_row[
                                "avg_speed_uncertainty_kmh"
                            ],
                            "physical_quantity_score": benchmark_row[
                                "physical_quantity_score"
                            ],
                            "effective_processing_fps": benchmark_row[
                                "effective_processing_fps"
                            ],
                            "mean_speed_kmh": benchmark_row["mean_speed_kmh"],
                            "tuning_score": tuning_score(benchmark_row),
                        },
                    )
                except Exception as exc:  # noqa: BLE001
                    trial.update(
                        {
                            "status": "failed",
                            "error": str(exc),
                            "quality_status": "fail",
                            "quality_issues": ["analysis_failed"],
                            "tuning_score": 0.0,
                        },
                    )
                rows.append(trial)

    ranked_rows = sorted(
        rows,
        key=lambda row: (
            row["tuning_score"],
            row.get("speed_tracks", 0),
            row.get("effective_processing_fps", 0.0),
        ),
        reverse=True,
    )
    successful = [row for row in rows if row["status"] == "ok"]
    return {
        "clip": args.clip,
        "device": device,
        "model_path": model_path,
        "trial_count": len(rows),
        "successful_trial_count": len(successful),
        "best_trial": ranked_rows[0] if ranked_rows else None,
        "avg_tuning_score": mean(row["tuning_score"] for row in successful)
        if successful
        else None,
        "rows": ranked_rows,
    }


def render_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Real Video Parameter Tuning Report",
        "",
        f"- Clip: `{summary['clip']}`",
        f"- Device: `{summary['device']}`",
        f"- Trials: {summary['successful_trial_count']}/{summary['trial_count']} successful",
        f"- Average tuning score: {summary['avg_tuning_score']}",
        "",
        "## Best Trial",
        "",
    ]
    best = summary["best_trial"]
    if best is None:
        lines.append("No successful trial.")
    else:
        lines.extend(
            [
                f"- Confidence: `{best['confidence_threshold']}`",
                f"- Frame stride: `{best['frame_stride']}`",
                f"- Max frames: `{best['max_frames']}`",
                f"- Quality: `{best['quality_status']}`",
                f"- Tuning score: `{best['tuning_score']:.3f}`",
                f"- Speed tracks: `{best.get('speed_tracks')}`",
                f"- Avg confidence: `{best.get('avg_speed_confidence')}`",
                f"- Avg uncertainty: `{best.get('avg_speed_uncertainty_kmh')} km/h`",
                f"- Physical quantity score: `{best.get('physical_quantity_score')}`",
                f"- Effective FPS: `{best.get('effective_processing_fps')}`",
            ],
        )
    lines.extend(
        [
            "",
            "## Trial Matrix",
            "",
            "| Conf | Stride | Frames | Score | Quality | Tracks | Speed tracks | "
            "Confidence | Uncertainty | Physics | FPS | Issues |",
            "| ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ],
    )
    for row in summary["rows"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row["confidence_threshold"]),
                    str(row["frame_stride"]),
                    str(row["max_frames"]),
                    f"{row['tuning_score']:.3f}",
                    row["quality_status"],
                    str(row.get("active_tracks", "N/A")),
                    str(row.get("speed_tracks", "N/A")),
                    _format(row.get("avg_speed_confidence")),
                    _format(row.get("avg_speed_uncertainty_kmh")),
                    _format(row.get("physical_quantity_score")),
                    _format(row.get("effective_processing_fps")),
                    ", ".join(row.get("quality_issues", [])),
                ],
            )
            + " |",
        )
    lines.extend(
        [
            "",
            "## Scoring Rationale",
            "",
            (
                "The tuning score balances quality gate status, speed confidence, "
                "speed uncertainty, physical quantity coverage, processing FPS, and "
                "available speed-track count. Manual calibration remains a hard "
                "requirement for industrial-grade absolute speed claims."
            ),
        ],
    )
    return "\n".join(lines) + "\n"


def _format(value: object) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a parameter sweep for real-video supervision analysis.",
    )
    parser.add_argument("--input-dir", default="data/tests/real_video_clips")
    parser.add_argument("--clip", default="028_red_light_static_0008s_30s.mp4")
    parser.add_argument("--output-dir", default="data/outputs/real_video_tuning")
    parser.add_argument("--calibration-presets", default="data/tests/calibration_presets.json")
    parser.add_argument("--confidences", default="0.25,0.35,0.45")
    parser.add_argument("--frame-strides", default="8,10,15")
    parser.add_argument("--max-frames-values", default="18,24")
    parser.add_argument("--model", default=None)
    parser.add_argument("--device", default="cpu")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    summary = run_tuning(args)
    (output_dir / "tuning_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
    )
    (output_dir / "tuning_report.md").write_text(render_markdown(summary))
    print(
        json.dumps(
            {
                "trial_count": summary["trial_count"],
                "successful_trial_count": summary["successful_trial_count"],
                "best_trial": summary["best_trial"],
                "output_dir": str(output_dir),
            },
            ensure_ascii=False,
            indent=2,
        ),
    )


if __name__ == "__main__":
    main()
