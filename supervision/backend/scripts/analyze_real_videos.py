from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/mpl")

import cv2
import torch
from domain.calibration.models import CalibrationPoint, HomographyResult
from domain.calibration.service import CalibrationService
from domain.detection.service import DetectionService
from domain.zones.models import ZoneConfig
from infrastructure.cv.supervision_adapter import SupervisionRuntimeAdapter
from infrastructure.cv.video_processor import OpenCVVideoFrameSource, SupervisionVideoProcessor
from shared.configs.settings import Settings

SEMANTIC_TRAFFIC_CLASS_IDS = {0, 1, 2, 3, 5, 7, 9, 10, 11}


@dataclass(frozen=True)
class SceneProfile:
    name: str
    world_width_m: float
    world_length_m: float
    position_rmse_floor_m: float
    calibration_scale_uncertainty_pct: float
    line_y_ratio: float
    line_x_start_ratio: float
    line_x_end_ratio: float
    notes: str


@dataclass(frozen=True)
class VideoCalibrationPreset:
    clip: str
    points: list[CalibrationPoint]
    position_rmse_floor_m: float
    calibration_scale_uncertainty_pct: float
    notes: str


@dataclass(frozen=True)
class CalibrationPresetCatalog:
    scene_profiles: dict[str, SceneProfile]
    video_calibrations: dict[str, VideoCalibrationPreset]


def default_profile_for_clip(path: Path) -> SceneProfile:
    name = path.name
    if "pedestrian" in name:
        return SceneProfile(
            name="pedestrian_high_view",
            world_width_m=22.0,
            world_length_m=45.0,
            position_rmse_floor_m=1.2,
            calibration_scale_uncertainty_pct=8.0,
            line_y_ratio=0.68,
            line_x_start_ratio=0.10,
            line_x_end_ratio=0.90,
            notes=(
                "high-view pedestrian/cyclist preset; higher process noise and "
                "crowd-aware routing"
            ),
        )
    if "dense_city_traffic_4k" in name:
        return SceneProfile(
            name="dense_city_traffic_4k",
            world_width_m=38.0,
            world_length_m=110.0,
            position_rmse_floor_m=2.0,
            calibration_scale_uncertainty_pct=12.0,
            line_y_ratio=0.70,
            line_x_start_ratio=0.18,
            line_x_end_ratio=0.86,
            notes=(
                "4K dense elevated traffic preset; larger uncertainty floor due "
                "long-range perspective"
            ),
        )
    if "red_light" in name:
        return SceneProfile(
            name="red_light_static",
            world_width_m=24.0,
            world_length_m=65.0,
            position_rmse_floor_m=1.5,
            calibration_scale_uncertainty_pct=8.0,
            line_y_ratio=0.72,
            line_x_start_ratio=0.20,
            line_x_end_ratio=0.86,
            notes="signalized road preset focused on approach and stop-line behavior",
        )
    return SceneProfile(
        name="wide_signalized_intersection",
        world_width_m=28.0,
        world_length_m=75.0,
        position_rmse_floor_m=1.5,
        calibration_scale_uncertainty_pct=8.0,
        line_y_ratio=0.72,
        line_x_start_ratio=0.18,
        line_x_end_ratio=0.88,
        notes="wide fixed elevated intersection preset",
    )


def _parse_calibration_point(value: dict[str, float]) -> CalibrationPoint:
    return CalibrationPoint(
        pixel_x=value["pixel_x"],
        pixel_y=value["pixel_y"],
        world_x=value["world_x"],
        world_y=value["world_y"],
    )


def load_calibration_presets(path: Path) -> CalibrationPresetCatalog:
    if not path.exists():
        return CalibrationPresetCatalog(scene_profiles={}, video_calibrations={})
    payload = json.loads(path.read_text())
    profiles: dict[str, SceneProfile] = {}
    for name, value in payload.get("scene_profiles", {}).items():
        profiles[name] = SceneProfile(name=name, **value)
    video_calibrations: dict[str, VideoCalibrationPreset] = {}
    for clip, value in payload.get("video_calibrations", {}).items():
        points = [_parse_calibration_point(point) for point in value["points"]]
        video_calibrations[clip] = VideoCalibrationPreset(
            clip=clip,
            points=points,
            position_rmse_floor_m=value["position_rmse_floor_m"],
            calibration_scale_uncertainty_pct=value[
                "calibration_scale_uncertainty_pct"
            ],
            notes=value.get("notes", ""),
        )
    return CalibrationPresetCatalog(
        scene_profiles=profiles,
        video_calibrations=video_calibrations,
    )


def profile_for_clip(
    path: Path,
    scene_profiles: dict[str, SceneProfile] | None = None,
) -> SceneProfile:
    fallback = default_profile_for_clip(path)
    if scene_profiles is None:
        return fallback
    return scene_profiles.get(fallback.name, fallback)


def build_profile_calibration(
    width: int,
    height: int,
    profile: SceneProfile,
) -> HomographyResult:
    left_bottom = (0.20 * width, 0.92 * height)
    right_bottom = (0.86 * width, 0.92 * height)
    right_top = (0.62 * width, 0.44 * height)
    left_top = (0.38 * width, 0.44 * height)
    points = [
        CalibrationPoint(*left_bottom, 0.0, 0.0),
        CalibrationPoint(*right_bottom, profile.world_width_m, 0.0),
        CalibrationPoint(*right_top, profile.world_width_m, profile.world_length_m),
        CalibrationPoint(*left_top, 0.0, profile.world_length_m),
        CalibrationPoint(
            (left_bottom[0] + right_bottom[0]) / 2.0,
            left_bottom[1],
            profile.world_width_m / 2.0,
            0.0,
        ),
        CalibrationPoint(
            (left_top[0] + right_top[0]) / 2.0,
            left_top[1],
            profile.world_width_m / 2.0,
            profile.world_length_m,
        ),
    ]
    return CalibrationService().compute_homography_ransac(points, random_seed=11)


def build_calibration(
    width: int,
    height: int,
    profile: SceneProfile,
    video_preset: VideoCalibrationPreset | None,
) -> HomographyResult:
    if video_preset is not None:
        return CalibrationService().compute_homography_ransac(
            video_preset.points,
            random_seed=11,
        )
    return build_profile_calibration(width, height, profile)


def build_zone(width: int, height: int, profile: SceneProfile) -> ZoneConfig:
    y = height * profile.line_y_ratio
    return ZoneConfig(
        name="analysis_line",
        line_start=[width * profile.line_x_start_ratio, y],
        line_end=[width * profile.line_x_end_ratio, y],
    )


def inspect_video(path: Path) -> dict[str, Any]:
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise ValueError(f"could not open video: {path}")
    try:
        return {
            "width": int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)),
            "height": int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            "fps": float(capture.get(cv2.CAP_PROP_FPS) or 24.0),
            "frame_count": int(capture.get(cv2.CAP_PROP_FRAME_COUNT)),
        }
    finally:
        capture.release()


def resolve_device(requested: str) -> str:
    if requested != "auto":
        return requested
    return "mps" if torch.backends.mps.is_available() else "cpu"


def analyze_clip(
    path: Path,
    model_path: str,
    device: str,
    confidence: float,
    frame_stride: int,
    max_frames: int,
    presets: CalibrationPresetCatalog,
) -> dict[str, Any]:
    metadata = inspect_video(path)
    profile = profile_for_clip(path, presets.scene_profiles)
    video_preset = presets.video_calibrations.get(path.name)
    calibration = build_calibration(
        metadata["width"],
        metadata["height"],
        profile,
        video_preset,
    )
    zone = build_zone(metadata["width"], metadata["height"], profile)
    rmse_floor_m = (
        video_preset.position_rmse_floor_m
        if video_preset is not None
        else profile.position_rmse_floor_m
    )
    scale_uncertainty_pct = (
        video_preset.calibration_scale_uncertainty_pct
        if video_preset is not None
        else profile.calibration_scale_uncertainty_pct
    )
    detector = DetectionService(
        model_path=model_path,
        device=device,
        confidence_threshold=confidence,
        allowed_class_ids=SEMANTIC_TRAFFIC_CLASS_IDS,
    )
    processor = SupervisionVideoProcessor(
        detector=detector,
        adapter=SupervisionRuntimeAdapter(),
        calibration=calibration,
        zone=zone,
        fps=metadata["fps"],
        segment_length_m=profile.world_length_m,
        position_rmse_floor_m=rmse_floor_m,
    )
    started = time.perf_counter()
    report = processor.process_frames(
        OpenCVVideoFrameSource(
            str(path),
            max_frames=max_frames,
            frame_stride=frame_stride,
        ).frames()
    )
    elapsed = time.perf_counter() - started
    processed_frames = min(max_frames, max(0, metadata["frame_count"] // frame_stride))
    return {
        "clip": path.name,
        "metadata": metadata,
        "scene_profile": asdict(profile),
        "device": device,
        "model_path": model_path,
        "confidence_threshold": confidence,
        "frame_stride": frame_stride,
        "max_frames": max_frames,
        "processed_frame_estimate": processed_frames,
        "elapsed_sec": elapsed,
        "effective_processing_fps": processed_frames / elapsed if elapsed > 0 else 0.0,
        "calibration": {
            "source": "video_manual_preset" if video_preset else "scene_profile_preset",
            "quality": calibration.calibration_quality,
            "rmse": calibration.reprojection_rmse,
            "inlier_count": calibration.inlier_count,
            "position_rmse_floor_m": rmse_floor_m,
            "scale_uncertainty_pct": scale_uncertainty_pct,
            "notes": video_preset.notes if video_preset is not None else profile.notes,
        },
        "sensitivity": build_sensitivity_report(report, scale_uncertainty_pct),
        "final_report": report,
    }


def build_sensitivity_report(
    report: dict[str, Any],
    scale_uncertainty_pct: float,
) -> dict[str, Any]:
    scale = scale_uncertainty_pct / 100.0
    active_speeds = [
        track["speed_kmh"]
        for track in report.get("active_tracks", [])
        if track.get("speed_kmh") is not None
    ]
    traffic_flow = report.get("traffic_flow", {})
    space_mean_speed = traffic_flow.get("space_mean_speed_kmh")
    return {
        "scale_uncertainty_pct": scale_uncertainty_pct,
        "speed_band_kmh": [
            min(active_speeds) * (1.0 - scale) if active_speeds else None,
            max(active_speeds) * (1.0 + scale) if active_speeds else None,
        ],
        "space_mean_speed_band_kmh": [
            space_mean_speed * (1.0 - scale)
            if space_mean_speed is not None
            else None,
            space_mean_speed * (1.0 + scale)
            if space_mean_speed is not None
            else None,
        ],
        "interpretation": (
            "World-scale calibration uncertainty changes all planar distances and "
            "speed estimates approximately linearly."
        ),
    }


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    successful = [result for result in results if result.get("status") == "ok"]
    speeds = [
        track["speed_kmh"]
        for result in successful
        for track in result["final_report"].get("active_tracks", [])
        if track.get("speed_kmh") is not None
    ]
    confidences = [
        track["speed_confidence"]
        for result in successful
        for track in result["final_report"].get("active_tracks", [])
        if track.get("speed_confidence") is not None
    ]
    return {
        "total_clips": len(results),
        "successful_clips": len(successful),
        "failed_clips": len(results) - len(successful),
        "avg_speed_kmh": sum(speeds) / len(speeds) if speeds else None,
        "avg_speed_confidence": sum(confidences) / len(confidences) if confidences else None,
        "mps_available": torch.backends.mps.is_available(),
        "mps_built": torch.backends.mps.is_built(),
    }


def select_clips(
    input_dir: Path,
    limit: int,
    sample_per_profile: int,
    presets: CalibrationPresetCatalog,
    clip_names: list[str] | None = None,
) -> list[Path]:
    clips = sorted(input_dir.glob("*.mp4"))
    if clip_names:
        by_name = {path.name: path for path in clips}
        missing = [name for name in clip_names if name not in by_name]
        if missing:
            raise ValueError(f"requested clips were not found: {', '.join(missing)}")
        return [by_name[name] for name in clip_names]
    if sample_per_profile <= 0:
        return clips[:limit]

    selected: list[Path] = []
    counts: dict[str, int] = {}
    for path in clips:
        profile_name = profile_for_clip(path, presets.scene_profiles).name
        if counts.get(profile_name, 0) >= sample_per_profile:
            continue
        selected.append(path)
        counts[profile_name] = counts.get(profile_name, 0) + 1
        if limit > 0 and len(selected) >= limit:
            break
    return selected


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze real traffic clips with YOLO + supervision.",
    )
    parser.add_argument("--input-dir", default="data/tests/real_video_clips")
    parser.add_argument("--output-dir", default="data/outputs/real_video_analysis")
    parser.add_argument("--calibration-presets", default="data/tests/calibration_presets.json")
    parser.add_argument("--limit", type=int, default=2)
    parser.add_argument(
        "--clips",
        nargs="*",
        default=None,
        help="Exact MP4 filenames to analyze in order, overriding --limit.",
    )
    parser.add_argument(
        "--sample-per-profile",
        type=int,
        default=0,
        help="Select N clips from each inferred traffic scene profile.",
    )
    parser.add_argument("--max-frames", type=int, default=45)
    parser.add_argument("--frame-stride", type=int, default=15)
    parser.add_argument("--confidence", type=float, default=0.35)
    parser.add_argument("--model", default=None)
    parser.add_argument("--device", default="auto")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = Settings()
    model_path = args.model or settings.cv.yolo_model
    device = resolve_device(args.device)
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    presets = load_calibration_presets(Path(args.calibration_presets))
    output_dir.mkdir(parents=True, exist_ok=True)
    clips = select_clips(
        input_dir,
        args.limit,
        args.sample_per_profile,
        presets,
        clip_names=args.clips,
    )
    results: list[dict[str, Any]] = []
    for path in clips:
        try:
            result = analyze_clip(
                path=path,
                model_path=model_path,
                device=device,
                confidence=args.confidence,
                frame_stride=args.frame_stride,
                max_frames=args.max_frames,
                presets=presets,
            )
            result["status"] = "ok"
        except Exception as exc:  # noqa: BLE001
            result = {"clip": path.name, "status": "failed", "error": str(exc)}
        results.append(result)
        (output_dir / f"{path.stem}.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
        )

    summary = summarize(results)
    summary_payload = {"summary": summary, "results": results}
    (output_dir / "summary.json").write_text(
        json.dumps(summary_payload, ensure_ascii=False, indent=2),
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
