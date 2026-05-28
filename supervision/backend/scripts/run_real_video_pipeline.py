from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/mpl")

from scripts.analyze_real_videos import main as analyze_main
from scripts.prepare_calibration_assets import prepare_assets
from scripts.summarize_real_video_benchmark import build_benchmark_summary, render_markdown
from scripts.validate_calibration_presets import render_markdown as render_validation_markdown
from scripts.validate_calibration_presets import validate_catalog


def apply_tuning_summary(args: argparse.Namespace) -> dict[str, Any] | None:
    tuning_summary = getattr(args, "tuning_summary", None)
    if not tuning_summary:
        return None
    payload = json.loads(Path(tuning_summary).read_text())
    best = payload.get("best_trial") or {}
    tuned_clip = best.get("clip") or payload.get("clip")
    if args.clips and tuned_clip not in args.clips:
        return {
            "source": tuning_summary,
            "applied": False,
            "reason": "best trial clip is not in requested clips",
            "clip": tuned_clip,
        }
    args.confidence = float(best["confidence_threshold"])
    args.frame_stride = int(best["frame_stride"])
    args.max_frames = int(best["max_frames"])
    if best.get("device"):
        args.device = str(best["device"])
    return {
        "source": tuning_summary,
        "applied": True,
        "clip": tuned_clip,
        "confidence": args.confidence,
        "frame_stride": args.frame_stride,
        "max_frames": args.max_frames,
        "device": args.device,
        "tuning_score": best.get("tuning_score"),
    }


def _run_analyze(args: argparse.Namespace, output_dir: Path) -> None:
    previous_argv = sys.argv[:]
    try:
        sys.argv = [
            "analyze_real_videos.py",
            "--input-dir",
            args.input_dir,
            "--output-dir",
            str(output_dir),
            "--calibration-presets",
            args.calibration_presets,
            "--max-frames",
            str(args.max_frames),
            "--frame-stride",
            str(args.frame_stride),
            "--confidence",
            str(args.confidence),
            "--device",
            args.device,
        ]
        if args.clips:
            sys.argv.extend(["--clips", *args.clips])
        else:
            sys.argv.extend(["--limit", str(args.limit)])
            if args.sample_per_profile > 0:
                sys.argv.extend(["--sample-per-profile", str(args.sample_per_profile)])
        analyze_main()
    finally:
        sys.argv = previous_argv


def run_pipeline(args: argparse.Namespace) -> dict[str, Any]:
    tuning_application = apply_tuning_summary(args)
    output_root = Path(args.output_dir)
    calibration_dir = output_root / "calibration_assets"
    analysis_dir = output_root / "analysis"
    validation_dir = output_root / "calibration_validation"

    prepare_assets(
        input_dir=Path(args.input_dir),
        output_dir=calibration_dir,
        limit=args.limit,
        frame_index=args.frame_index,
        clip_names=args.clips,
    )

    validation = validate_catalog(
        Path(args.calibration_presets),
        required_clips=args.clips,
    )
    validation_dir.mkdir(parents=True, exist_ok=True)
    (validation_dir / "calibration_validation.json").write_text(
        json.dumps(validation, ensure_ascii=False, indent=2),
    )
    (validation_dir / "calibration_validation.md").write_text(
        render_validation_markdown(validation),
    )

    _run_analyze(args, analysis_dir)
    analysis_payload = json.loads((analysis_dir / "summary.json").read_text())
    benchmark = build_benchmark_summary(analysis_payload)
    (analysis_dir / "benchmark_summary.json").write_text(
        json.dumps(benchmark, ensure_ascii=False, indent=2),
    )
    (analysis_dir / "benchmark_report.md").write_text(render_markdown(benchmark))

    manifest = {
        "output_root": str(output_root),
        "calibration_assets": str(calibration_dir),
        "calibration_validation": str(validation_dir),
        "analysis": str(analysis_dir),
        "clips": args.clips,
        "analysis_parameters": {
            "confidence": args.confidence,
            "frame_stride": args.frame_stride,
            "max_frames": args.max_frames,
            "device": args.device,
        },
        "tuning_application": tuning_application,
        "quality_counts": benchmark["quality_counts"],
        "manual_calibration_count": validation["video_calibration_count"],
    }
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "pipeline_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
    )
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run calibration asset export, validation, real video analysis, and benchmark.",
    )
    parser.add_argument("--input-dir", default="data/tests/real_video_clips")
    parser.add_argument("--output-dir", default="data/outputs/real_video_pipeline")
    parser.add_argument("--calibration-presets", default="data/tests/calibration_presets.json")
    parser.add_argument("--clips", nargs="*", default=None)
    parser.add_argument("--limit", type=int, default=4)
    parser.add_argument("--sample-per-profile", type=int, default=0)
    parser.add_argument("--frame-index", type=int, default=1)
    parser.add_argument("--max-frames", type=int, default=24)
    parser.add_argument("--frame-stride", type=int, default=10)
    parser.add_argument("--confidence", type=float, default=0.35)
    parser.add_argument("--device", default="cpu")
    parser.add_argument(
        "--tuning-summary",
        default=None,
        help="Optional tuning_summary.json whose best trial should override analysis parameters.",
    )
    return parser.parse_args()


def main() -> None:
    manifest = run_pipeline(parse_args())
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
