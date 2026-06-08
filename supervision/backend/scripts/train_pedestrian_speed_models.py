from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from domain.speed.pedestrian_training import (
    PEDESTRIAN_OUTPUT_DIR,
    build_speed_jump_baseline_comparison,
    build_training_manifest,
    filter_manifest_to_existing_clips,
    generate_pseudo_labels,
    load_analysis_payloads,
    write_training_outputs,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train same-camera pedestrian speed quality models for clips 033-042.",
    )
    parser.add_argument("--analysis-dir", default="data/outputs/real_video_analysis")
    parser.add_argument("--input-dir", default="data/tests/real_video_clips")
    parser.add_argument("--output-dir", default=str(PEDESTRIAN_OUTPUT_DIR))
    parser.add_argument("--analyze-missing", action="store_true")
    parser.add_argument("--max-frames", type=int, default=0)
    parser.add_argument("--frame-stride", type=int, default=1)
    parser.add_argument("--confidence", type=float, default=0.45)
    parser.add_argument("--device", default="auto")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    full_manifest = build_training_manifest()
    manifest, skipped_source_missing = filter_manifest_to_existing_clips(
        Path(args.input_dir),
        full_manifest,
    )
    analysis_dir = Path(args.analysis_dir)
    payloads = load_analysis_payloads(analysis_dir, manifest)
    missing = [item.clip_name for item in manifest if item.clip_name not in payloads]
    if missing and args.analyze_missing:
        _run_missing_analysis(args, missing)
        payloads = load_analysis_payloads(analysis_dir, manifest)
        missing = [item.clip_name for item in manifest if item.clip_name not in payloads]
    rows = generate_pseudo_labels(payloads, manifest)
    if not rows:
        raise SystemExit(
            "No pseudo labels were generated. Run with --analyze-missing or point "
            "--analysis-dir at JSON outputs containing frame_reports.",
        )
    paths = write_training_outputs(rows, Path(args.output_dir), manifest)
    summary_path = Path(paths["benchmark_summary"])
    summary = json.loads(summary_path.read_text())
    summary["missing_analysis_clips"] = missing
    summary["skipped_source_missing_clips"] = [
        item.clip_name for item in skipped_source_missing
    ]
    summary["speed_jump_baseline_comparison"] = build_speed_jump_baseline_comparison(
        payloads,
        manifest,
    )
    summary["outputs"] = {name: str(path) for name, path in paths.items()}
    summary_path.write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


def _run_missing_analysis(args: argparse.Namespace, missing: list[str]) -> None:
    command = [
        sys.executable,
        str(Path(__file__).with_name("analyze_real_videos.py")),
        "--input-dir",
        str(args.input_dir),
        "--output-dir",
        str(args.analysis_dir),
        "--clips",
        *missing,
        "--max-frames",
        str(args.max_frames),
        "--frame-stride",
        str(args.frame_stride),
        "--confidence",
        str(args.confidence),
        "--device",
        str(args.device),
    ]
    subprocess.run(command, check=True)


if __name__ == "__main__":
    main()
