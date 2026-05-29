from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import asdict, dataclass
from fnmatch import fnmatch
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/mpl")

import cv2
import torch
import yaml
from domain.auto_calibration.models import CandidateLine
from domain.auto_calibration.service import AutoCalibrationService
from domain.calibration.models import CalibrationPoint, HomographyResult
from domain.calibration.service import CalibrationService
from domain.detection.service import DetectionService
from domain.zones.models import ZoneConfig
from infrastructure.cv.auto_calibration_extractor import FrameGeometryExtractor
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
class CameraProfilePreset:
    profile_id: str
    display_name: str
    role: str
    covered_clip_patterns: list[str]
    world_width_m: float
    world_length_m: float
    grid_spacing_m: float
    position_rmse_floor_m: float
    calibration_scale_uncertainty_pct: float
    manual_control_points: list[CalibrationPoint]
    tuning: dict[str, Any]
    traffic_line_zones: list[dict[str, Any]]
    polygon_zones: list[dict[str, Any]]
    traffic_light_rois: list[dict[str, Any]]
    risk_areas: list[dict[str, Any]]
    quality_gates: dict[str, Any]
    fallback_policy: str
    auto_candidate_lines: list[CandidateLine]
    scale_prior_used: str | None


@dataclass(frozen=True)
class CalibrationPresetCatalog:
    scene_profiles: dict[str, SceneProfile]
    video_calibrations: dict[str, VideoCalibrationPreset]
    camera_profiles: dict[str, CameraProfilePreset] | None = None


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


def _parse_candidate_line(value: dict[str, Any]) -> CandidateLine:
    return CandidateLine(
        name=str(value["name"]),
        kind=str(value.get("kind", "road_edge")),
        start=(float(value["start"][0]), float(value["start"][1])),
        end=(float(value["end"][0]), float(value["end"][1])),
    )


def _load_calibration_payload(path: Path) -> dict[str, Any]:
    if path.suffix.lower() in {".yaml", ".yml"}:
        payload = yaml.safe_load(path.read_text())
        return payload if isinstance(payload, dict) else {}
    return json.loads(path.read_text())


def load_camera_profiles(path: Path) -> dict[str, CameraProfilePreset]:
    if not path.exists():
        return {}
    payload = _load_calibration_payload(path)
    profiles: dict[str, CameraProfilePreset] = {}
    for profile_id, value in payload.get("camera_profiles", {}).items():
        auto_candidates = value.get("auto_calibration_candidates", {})
        profiles[profile_id] = CameraProfilePreset(
            profile_id=profile_id,
            display_name=value["display_name"],
            role=value["role"],
            covered_clip_patterns=list(value["covered_clip_patterns"]),
            world_width_m=float(value["world_width_m"]),
            world_length_m=float(value["world_length_m"]),
            grid_spacing_m=float(value.get("grid_spacing_m", 5.0)),
            position_rmse_floor_m=float(value["position_rmse_floor_m"]),
            calibration_scale_uncertainty_pct=float(
                value["calibration_scale_uncertainty_pct"],
            ),
            manual_control_points=[
                _parse_calibration_point(point)
                for point in value["manual_control_points"]
            ],
            tuning=dict(value.get("tuning", {})),
            traffic_line_zones=list(value.get("traffic_line_zones", [])),
            polygon_zones=list(value.get("polygon_zones", [])),
            traffic_light_rois=list(value.get("traffic_light_rois", [])),
            risk_areas=list(value.get("risk_areas", [])),
            quality_gates=dict(value.get("quality_gates", {})),
            fallback_policy=str(value.get("fallback_policy", "")),
            auto_candidate_lines=[
                _parse_candidate_line(line)
                for line in auto_candidates.get("candidate_lines", [])
            ],
            scale_prior_used=auto_candidates.get("scale_prior_used")
            or value.get("scale_prior_used"),
        )
    return profiles


def load_calibration_presets(path: Path) -> CalibrationPresetCatalog:
    if not path.exists():
        return CalibrationPresetCatalog(scene_profiles={}, video_calibrations={})
    payload = _load_calibration_payload(path)
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
        camera_profiles={},
    )


def match_camera_profile(
    path: Path,
    camera_profiles: dict[str, CameraProfilePreset] | None,
) -> CameraProfilePreset | None:
    if not camera_profiles:
        return None
    for profile in camera_profiles.values():
        if any(fnmatch(path.name, pattern) for pattern in profile.covered_clip_patterns):
            return profile
    return None


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


def build_camera_profile_calibration(profile: CameraProfilePreset) -> HomographyResult:
    return CalibrationService().compute_homography_ransac(
        profile.manual_control_points,
        random_seed=11,
    )


def build_zone(width: int, height: int, profile: SceneProfile) -> ZoneConfig:
    y = height * profile.line_y_ratio
    return ZoneConfig(
        name="analysis_line",
        line_start=[width * profile.line_x_start_ratio, y],
        line_end=[width * profile.line_x_end_ratio, y],
    )


def build_camera_profile_zone(
    width: int,
    height: int,
    camera_profile: CameraProfilePreset,
) -> ZoneConfig:
    first_zone = camera_profile.traffic_line_zones[0]
    start_ratio = first_zone["line_start_ratio"]
    end_ratio = first_zone["line_end_ratio"]
    return ZoneConfig(
        name=str(first_zone["name"]),
        line_start=[width * float(start_ratio[0]), height * float(start_ratio[1])],
        line_end=[width * float(end_ratio[0]), height * float(end_ratio[1])],
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
    max_frames: int | None,
    presets: CalibrationPresetCatalog,
    processed_output_dir: Path | None = None,
) -> dict[str, Any]:
    if frame_stride <= 0:
        raise ValueError("frame_stride must be positive")
    metadata = inspect_video(path)
    profile = profile_for_clip(path, presets.scene_profiles)
    camera_profile = match_camera_profile(path, presets.camera_profiles)
    video_preset = presets.video_calibrations.get(path.name)
    auto_diagnostics = None
    frame_geometry_evidence = None
    if camera_profile is not None:
        calibration = build_camera_profile_calibration(camera_profile)
        zone = build_camera_profile_zone(
            metadata["width"],
            metadata["height"],
            camera_profile,
        )
        frame_geometry_evidence = FrameGeometryExtractor().extract_from_video(path)
        candidate_lines = [
            *camera_profile.auto_candidate_lines,
            *frame_geometry_evidence.candidate_lines,
        ]
        auto_diagnostics = AutoCalibrationService().diagnose(
            candidate_lines,
            camera_profile.scale_prior_used,
            manual_profile_available=True,
            evidence_sources=["camera_profile_candidates", "frame_hough_lines"],
            world_width_m=camera_profile.world_width_m,
            world_length_m=camera_profile.world_length_m,
        )
    else:
        calibration = build_calibration(
            metadata["width"],
            metadata["height"],
            profile,
            video_preset,
        )
        zone = build_zone(metadata["width"], metadata["height"], profile)
    rmse_floor_m = (
        camera_profile.position_rmse_floor_m
        if camera_profile is not None
        else
        video_preset.position_rmse_floor_m
        if video_preset is not None
        else profile.position_rmse_floor_m
    )
    scale_uncertainty_pct = (
        camera_profile.calibration_scale_uncertainty_pct
        if camera_profile is not None
        else
        video_preset.calibration_scale_uncertainty_pct
        if video_preset is not None
        else profile.calibration_scale_uncertainty_pct
    )
    confidence = float(
        camera_profile.tuning.get("confidence_threshold", confidence)
        if camera_profile is not None
        else confidence,
    )
    detector = DetectionService(
        model_path=model_path,
        device=device,
        confidence_threshold=confidence,
        allowed_class_ids=SEMANTIC_TRAFFIC_CLASS_IDS,
    )
    rendered_video_path = (
        processed_output_dir / f"{path.stem}_processed.mp4"
        if processed_output_dir is not None
        else None
    )
    if processed_output_dir is not None:
        processed_output_dir.mkdir(parents=True, exist_ok=True)
    processor = SupervisionVideoProcessor(
        detector=detector,
        adapter=SupervisionRuntimeAdapter(),
        calibration=calibration,
        zone=zone,
        fps=metadata["fps"],
        frame_width=metadata["width"],
        frame_height=metadata["height"],
        segment_width_m=camera_profile.world_width_m
        if camera_profile
        else profile.world_width_m,
        segment_length_m=camera_profile.world_length_m
        if camera_profile
        else profile.world_length_m,
        grid_spacing_m=camera_profile.grid_spacing_m if camera_profile else 5.0,
        position_rmse_floor_m=rmse_floor_m,
        rendered_video_path=rendered_video_path,
        rendered_video_fps=max(metadata["fps"] / frame_stride, 1.0),
        calibration_context={
            "calibration_source": "camera_manual_preset"
            if camera_profile is not None
            else "video_manual_preset"
            if video_preset
            else "scene_profile_preset",
            "camera_profile_id": camera_profile.profile_id if camera_profile else None,
            "camera_profile_display_name": camera_profile.display_name
            if camera_profile
            else None,
            "camera_profile_role": camera_profile.role if camera_profile else None,
            "profile_polygon_zones": camera_profile.polygon_zones
            if camera_profile is not None
            else [],
            "profile_traffic_light_rois": camera_profile.traffic_light_rois
            if camera_profile is not None
            else [],
            "profile_risk_areas": camera_profile.risk_areas if camera_profile is not None else [],
            "profile_tuning": camera_profile.tuning if camera_profile is not None else {},
            "auto_calibration": auto_diagnostics.to_dict()
            if auto_diagnostics is not None
            else None,
            "frame_geometry_evidence": frame_geometry_evidence.to_dict()
            if frame_geometry_evidence is not None
            else None,
            "profile_reuse_note": (
                "fixed camera calibration reused by filename pattern"
                if camera_profile is not None
                else None
            ),
        },
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
    available_frames = max(0, (metadata["frame_count"] + frame_stride - 1) // frame_stride)
    processed_frames = (
        min(max_frames, available_frames) if max_frames is not None else available_frames
    )
    sensitivity = build_sensitivity_report(report, scale_uncertainty_pct)
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
            "source": "camera_manual_preset"
            if camera_profile is not None
            else "video_manual_preset"
            if video_preset
            else "scene_profile_preset",
            "camera_profile_id": camera_profile.profile_id if camera_profile else None,
            "camera_profile_role": camera_profile.role if camera_profile else None,
            "quality": calibration.calibration_quality,
            "rmse": calibration.reprojection_rmse,
            "inlier_count": calibration.inlier_count,
            "position_rmse_floor_m": rmse_floor_m,
            "scale_uncertainty_pct": scale_uncertainty_pct,
            "notes": camera_profile.fallback_policy
            if camera_profile is not None
            else video_preset.notes
            if video_preset is not None
            else profile.notes,
            "auto_calibration": auto_diagnostics.to_dict()
            if auto_diagnostics is not None
            else None,
            "frame_geometry_evidence": frame_geometry_evidence.to_dict()
            if frame_geometry_evidence is not None
            else None,
        },
        "processed_video": {
            "path": str(rendered_video_path) if rendered_video_path is not None else None,
            "filename": rendered_video_path.name if rendered_video_path is not None else None,
        },
        "sensitivity": sensitivity,
        "final_report": report
        | {
            "calibration_diagnostics": {
                "homography_model": "RANSAC planar homography, pixel(u,v) -> ground(X,Y)",
                "calibration_source": "camera_manual_preset"
                if camera_profile is not None
                else "video_manual_preset"
                if video_preset
                else "scene_profile_preset",
                "camera_profile_id": camera_profile.profile_id if camera_profile else None,
                "camera_profile_role": camera_profile.role if camera_profile else None,
                "profile_polygon_zones": camera_profile.polygon_zones
                if camera_profile is not None
                else [],
                "profile_traffic_light_rois": camera_profile.traffic_light_rois
                if camera_profile is not None
                else [],
                "profile_risk_areas": camera_profile.risk_areas
                if camera_profile is not None
                else [],
                "profile_reuse_note": (
                    "fixed camera calibration reused by filename pattern"
                    if camera_profile is not None
                    else None
                ),
                "auto_calibration": auto_diagnostics.to_dict()
                if auto_diagnostics is not None
                else None,
                "frame_geometry_evidence": frame_geometry_evidence.to_dict()
                if frame_geometry_evidence is not None
                else None,
                "calibration_quality": calibration.calibration_quality,
                "reprojection_rmse_px": calibration.reprojection_rmse,
                "inlier_count": calibration.inlier_count,
                "condition_number": calibration.condition_number,
                "position_rmse_m": rmse_floor_m,
                "scale_uncertainty_pct": scale_uncertainty_pct,
                "speed_band_kmh": sensitivity["speed_band_kmh"],
                "space_mean_speed_band_kmh": sensitivity["space_mean_speed_band_kmh"],
                "error_sources": [
                    "homography calibration residual",
                    "detector bounding-box jitter",
                    "frame timestamp quantization",
                    "perspective extrapolation outside calibrated road plane",
                ],
                "model_reference": "Model 1 + Model 3 + Model 6 + Model 10",
            },
        },
        "frame_reports": processor.frame_reports,
    }


def build_sensitivity_report(
    report: dict[str, Any],
    scale_uncertainty_pct: float,
) -> dict[str, Any]:
    scale = scale_uncertainty_pct / 100.0
    active_speeds = [
        track["speed_kmh"]
        for track in report.get("active_tracks", [])
        if track.get("speed_kmh") is not None and track.get("physics_valid", True)
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
    parser.add_argument("--calibration-presets", default="data/tests/calibration_presets.yaml")
    parser.add_argument("--camera-profiles", default="data/tests/camera_profiles.yaml")
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
    camera_profiles = load_camera_profiles(Path(args.camera_profiles))
    presets = CalibrationPresetCatalog(
        scene_profiles=presets.scene_profiles,
        video_calibrations=presets.video_calibrations,
        camera_profiles=camera_profiles,
    )
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
            max_frames = args.max_frames if args.max_frames > 0 else None
            result = analyze_clip(
                path=path,
                model_path=model_path,
                device=device,
                confidence=args.confidence,
                frame_stride=args.frame_stride,
                max_frames=max_frames,
                presets=presets,
                processed_output_dir=output_dir / "processed_videos",
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
