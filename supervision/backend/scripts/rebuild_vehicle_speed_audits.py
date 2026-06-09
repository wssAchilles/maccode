from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from statistics import mean
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from domain.speed.vehicle_diagnostics import (  # noqa: E402
    annotate_vehicle_speed_reports,
    build_vehicle_speed_aggregate,
    source_commit,
    write_vehicle_speed_audit,
)

from scripts.summarize_real_video_benchmark import (  # noqa: E402
    build_benchmark_summary,
    render_markdown,
)

SKIPPED_JSON_STEMS = {
    "benchmark_summary",
    "summary",
}
SKIPPED_JSON_SUFFIXES = (
    "_speed_audit",
    "_reaudit",
)


def collect_result_paths(
    inputs: list[Path],
    *,
    recursive: bool = False,
) -> list[Path]:
    paths: list[Path] = []
    for source in inputs:
        if source.is_file():
            paths.append(source)
            continue
        if not source.is_dir():
            continue
        iterator = source.rglob("*.json") if recursive else source.glob("*.json")
        paths.extend(sorted(iterator))
    return [
        path
        for path in sorted(dict.fromkeys(paths))
        if not _should_skip_json_path(path)
    ]


def rebuild_vehicle_speed_audits(
    inputs: list[Path],
    *,
    output_dir: Path,
    clips: set[str] | None = None,
    recursive: bool = False,
    reconstruction_applied: bool = True,
    speed_ground_truth_dir: Path | None = None,
    source_commit_value: str | None = None,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    diagnostics_dir = output_dir / "vehicle_speed_diagnostics"
    results: list[dict[str, Any]] = []
    for path in collect_result_paths(inputs, recursive=recursive):
        try:
            result = rebuild_vehicle_speed_audit(
                path,
                output_dir=output_dir,
                diagnostics_dir=diagnostics_dir,
                clips=clips,
                reconstruction_applied=reconstruction_applied,
                speed_ground_truth_dir=speed_ground_truth_dir,
                source_commit_value=source_commit_value,
            )
        except Exception as exc:  # noqa: BLE001
            result = {
                "clip": path.name,
                "status": "failed",
                "source_result_path": str(path),
                "error": str(exc),
            }
        if result is not None:
            results.append(result)

    summary = summarize_reaudit_results(results)
    payload = {
        "source_inputs": [str(path) for path in inputs],
        "output_dir": str(output_dir),
        "summary": summary,
        "results": results,
    }
    (output_dir / "summary.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    benchmark = build_benchmark_summary(payload)
    (output_dir / "benchmark_summary.json").write_text(
        json.dumps(benchmark, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "benchmark_report.md").write_text(
        render_markdown(benchmark),
        encoding="utf-8",
    )
    return payload


def rebuild_vehicle_speed_audit(
    path: Path,
    *,
    output_dir: Path,
    diagnostics_dir: Path,
    clips: set[str] | None,
    reconstruction_applied: bool,
    speed_ground_truth_dir: Path | None,
    source_commit_value: str | None,
) -> dict[str, Any] | None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    clip = str(payload.get("clip") or path.name)
    if clips is not None and clip not in clips and Path(clip).stem not in clips:
        return None
    frame_reports = payload.get("frame_reports")
    if not isinstance(frame_reports, list) or not frame_reports:
        return {
            "clip": clip,
            "status": "skipped",
            "skip_reason": "missing_frame_reports",
            "source_result_path": str(path),
        }

    annotated_reports = annotate_vehicle_speed_reports(
        frame_reports,
        reconstruction_applied=reconstruction_applied,
        source_commit_value=source_commit_value,
    )
    audit = write_vehicle_speed_audit(
        annotated_reports,
        clip=clip,
        processed_video_path=None,
        diagnostics_dir=diagnostics_dir,
        source_commit_value=source_commit_value,
        speed_ground_truth_dir=speed_ground_truth_dir,
    )
    result = _lightweight_result(payload, annotated_reports, audit, path)
    (output_dir / f"{Path(clip).stem}_reaudit.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return result


def summarize_reaudit_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    successful = [result for result in results if result.get("status") == "ok"]
    speeds = [
        track["speed_kmh"]
        for result in successful
        for track in result["final_report"].get("active_tracks", [])
        if track.get("speed_kmh") is not None and track.get("physics_valid", True)
    ]
    confidences = [
        track["speed_confidence"]
        for result in successful
        for track in result["final_report"].get("active_tracks", [])
        if track.get("speed_confidence") is not None and track.get("physics_valid", True)
    ]
    return {
        "total_clips": len(results),
        "successful_clips": len(successful),
        "failed_clips": sum(1 for result in results if result.get("status") == "failed"),
        "skipped_clips": sum(1 for result in results if result.get("status") == "skipped"),
        "avg_speed_kmh": mean(speeds) if speeds else None,
        "avg_speed_confidence": mean(confidences) if confidences else None,
        "vehicle_speed_aggregate": build_vehicle_speed_aggregate(successful),
        "mps_available": None,
        "mps_built": None,
    }


def _lightweight_result(
    payload: dict[str, Any],
    annotated_reports: list[dict[str, Any]],
    audit: dict[str, Any],
    source_path: Path,
) -> dict[str, Any]:
    clip = str(payload.get("clip") or source_path.name)
    final_report = _annotated_final_report(payload, annotated_reports)
    result = {
        "clip": clip,
        "status": "ok",
        "source_result_path": str(source_path),
        "reaudit_only": True,
        "frame_stride": payload.get("frame_stride"),
        "max_frames": payload.get("max_frames"),
        "processed_frame_estimate": payload.get("processed_frame_estimate"),
        "effective_processing_fps": payload.get("effective_processing_fps") or 0.0,
        "scene_profile": _scene_profile(payload),
        "calibration": _calibration(payload),
        "sensitivity": _sensitivity(payload),
        "final_report": _final_report(final_report),
        "vehicle_speed_audit": audit,
    }
    return result


def _annotated_final_report(
    payload: dict[str, Any],
    annotated_reports: list[dict[str, Any]],
) -> dict[str, Any]:
    annotated = _matching_annotated_report(payload.get("final_report"), annotated_reports)
    if annotated is None:
        return {}
    original = payload.get("final_report")
    if isinstance(original, dict):
        return {**original, **annotated}
    return annotated


def _matching_annotated_report(
    original_final_report: object,
    annotated_reports: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if not annotated_reports:
        return None
    if isinstance(original_final_report, dict):
        frame_index = original_final_report.get("frame_index")
        if frame_index is not None:
            for report in reversed(annotated_reports):
                if report.get("frame_index") == frame_index:
                    return report
    return annotated_reports[-1]


def _scene_profile(payload: dict[str, Any]) -> dict[str, Any]:
    value = payload.get("scene_profile")
    if isinstance(value, dict):
        return {**{"name": "unknown"}, **value}
    return {"name": "unknown"}


def _calibration(payload: dict[str, Any]) -> dict[str, Any]:
    value = payload.get("calibration")
    defaults = {
        "source": "unknown",
        "quality": "unknown",
        "position_rmse_floor_m": None,
        "scale_uncertainty_pct": None,
    }
    if isinstance(value, dict):
        return {**defaults, **value}
    return defaults


def _sensitivity(payload: dict[str, Any]) -> dict[str, Any]:
    value = payload.get("sensitivity")
    defaults = {"space_mean_speed_band_kmh": [None, None]}
    if isinstance(value, dict):
        return {**defaults, **value}
    return defaults


def _final_report(report: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(report)
    normalized.setdefault("active_tracks", [])
    normalized.setdefault("regional_people_count", {"people_count": 0})
    normalized.setdefault("infrastructure_semantics", {"traffic_light_count": 0})
    normalized.setdefault(
        "traffic_flow",
        {
            "space_mean_speed_kmh": None,
            "flow_q_veh_per_hour": None,
            "density_k_veh_per_km": None,
            "congestion_level": "unknown",
        },
    )
    normalized.setdefault(
        "safety_metrics",
        {
            "risk_level": "unknown",
            "min_time_to_collision_sec": None,
            "min_time_headway_sec": None,
        },
    )
    return normalized


def _should_skip_json_path(path: Path) -> bool:
    return path.stem in SKIPPED_JSON_STEMS or path.stem.endswith(SKIPPED_JSON_SUFFIXES)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rebuild vehicle speed audits from existing result JSON frame_reports.",
    )
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/outputs/vehicle_speed_reaudit"),
    )
    parser.add_argument("--clips", nargs="*", default=None)
    parser.add_argument("--recursive", action="store_true")
    parser.add_argument(
        "--reconstruction-applied",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument(
        "--speed-ground-truth-dir",
        type=Path,
        default=Path("data/tests/speed_ground_truth"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = rebuild_vehicle_speed_audits(
        list(args.inputs),
        output_dir=args.output_dir,
        clips=set(args.clips) if args.clips else None,
        recursive=bool(args.recursive),
        reconstruction_applied=bool(args.reconstruction_applied),
        speed_ground_truth_dir=args.speed_ground_truth_dir,
        source_commit_value=source_commit(Path.cwd()),
    )
    print(
        json.dumps(
            {
                "results": len(payload["results"]),
                "successful": payload["summary"]["successful_clips"],
                "skipped": payload["summary"]["skipped_clips"],
                "failed": payload["summary"]["failed_clips"],
                "output_dir": payload["output_dir"],
            },
            ensure_ascii=False,
            indent=2,
        ),
    )


if __name__ == "__main__":
    main()
