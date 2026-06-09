from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from domain.speed.vehicle_diagnostics import build_vehicle_speed_aggregate  # noqa: E402
from shared.configs.settings import Settings  # noqa: E402

from scripts.analyze_real_videos import (  # noqa: E402
    CalibrationPresetCatalog,
    analyze_clip,
    load_calibration_presets,
    load_camera_profiles,
    resolve_device,
    summarize,
)
from scripts.summarize_real_video_benchmark import (  # noqa: E402
    build_benchmark_summary,
    render_markdown,
)


def load_regression_set(path: Path, set_name: str | None) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    selected = set_name or str(payload.get("default_set") or "")
    sets = payload.get("sets") or {}
    if not selected or selected not in sets:
        raise ValueError(f"unknown vehicle speed regression set: {selected}")
    entry = sets[selected]
    if not isinstance(entry, dict):
        raise ValueError(f"invalid vehicle speed regression set: {selected}")
    return {"name": selected, **entry}


def available_clips(input_dir: Path, clip_names: list[str]) -> tuple[list[Path], list[str]]:
    by_name = {path.name: path for path in input_dir.glob("*.mp4")}
    selected = [by_name[name] for name in clip_names if name in by_name]
    missing = [name for name in clip_names if name not in by_name]
    return selected, missing


def selected_clip_names(regression_clips: list[str], requested: list[str] | None) -> list[str]:
    if requested is None:
        return regression_clips
    allowed = set(regression_clips)
    unknown = [name for name in requested if name not in allowed]
    if unknown:
        raise ValueError(
            "requested clips are not in the vehicle speed regression set: "
            + ", ".join(unknown),
        )
    return requested


def build_regression_summary(
    results: list[dict[str, Any]],
    regression_set: dict[str, Any],
) -> dict[str, Any]:
    summary = summarize(results)
    summary["vehicle_speed_aggregate"] = build_vehicle_speed_aggregate(
        results,
        dense_city_acceptance_min_coverage=float(
            regression_set.get("aggregate_min_coverage", 0.993),
        ),
        clip_acceptance_min_coverage=float(
            regression_set.get("clip_min_coverage", 0.995),
        ),
        car_hard_max_kmh=float(regression_set.get("max_car_speed_kmh", 160.0)),
    )
    return summary


def run_regression(args: argparse.Namespace) -> dict[str, Any]:
    settings = Settings()
    regression_set = load_regression_set(Path(args.regression_config), args.set)
    requested_clips = selected_clip_names(
        [str(name) for name in regression_set.get("clips", [])],
        args.clips,
    )
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    clips, missing = available_clips(input_dir, requested_clips)
    if not clips and not args.allow_empty:
        raise ValueError("no requested vehicle speed regression clips were found")

    preset_path = Path(args.calibration_presets)
    presets = load_calibration_presets(preset_path)
    presets = CalibrationPresetCatalog(
        scene_profiles=presets.scene_profiles,
        video_calibrations=presets.video_calibrations,
        camera_profiles=load_camera_profiles(Path(args.camera_profiles)),
    )
    device = resolve_device(args.device)
    model_path = args.model or settings.cv.yolo_model
    results: list[dict[str, Any]] = []
    max_frames = args.max_frames if args.max_frames > 0 else None
    for path in clips:
        try:
            result = analyze_clip(
                path=path,
                model_path=model_path,
                device=device,
                confidence=args.confidence,
                frame_stride=args.frame_stride,
                max_frames=max_frames,
                presets=presets,
                processed_output_dir=output_dir / "processed_videos",
                speed_ground_truth_dir=Path(args.speed_ground_truth_dir),
            )
            result["status"] = "ok"
        except Exception as exc:  # noqa: BLE001
            result = {"clip": path.name, "status": "failed", "error": str(exc)}
        results.append(result)
        (output_dir / f"{path.stem}.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    summary_payload = {
        "regression_set": regression_set,
        "missing_clips": missing,
        "summary": build_regression_summary(results, regression_set),
        "results": results,
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    benchmark = build_benchmark_summary(summary_payload)
    (output_dir / "benchmark_summary.json").write_text(
        json.dumps(benchmark, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "benchmark_report.md").write_text(
        render_markdown(benchmark),
        encoding="utf-8",
    )
    return summary_payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the fixed-camera vehicle speed regression suite.",
    )
    parser.add_argument("--regression-config", default="data/tests/vehicle_speed_regression.yaml")
    parser.add_argument("--set", default=None)
    parser.add_argument("--input-dir", default="data/tests/real_video_clips")
    parser.add_argument("--output-dir", default="data/outputs/vehicle_speed_regression")
    parser.add_argument("--calibration-presets", default="data/tests/calibration_presets.yaml")
    parser.add_argument("--camera-profiles", default="data/tests/camera_profiles.yaml")
    parser.add_argument("--max-frames", type=int, default=0)
    parser.add_argument("--frame-stride", type=int, default=1)
    parser.add_argument("--confidence", type=float, default=0.35)
    parser.add_argument("--model", default=None)
    parser.add_argument("--device", default="auto")
    parser.add_argument(
        "--speed-ground-truth-dir",
        default="data/tests/speed_ground_truth",
        help="Optional CSV directory for vehicle speed GT metrics.",
    )
    parser.add_argument(
        "--clips",
        nargs="*",
        default=None,
        help="Exact MP4 filenames from the regression set to run in order.",
    )
    parser.add_argument("--allow-empty", action="store_true")
    return parser.parse_args()


def main() -> None:
    payload = run_regression(parse_args())
    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
