from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import asdict, dataclass, field
from fnmatch import fnmatch
from pathlib import Path
from typing import Any

import numpy as np

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
from domain.calibration.validation import (
    manual_calibration_provenance_issues,
    validation_independent_segment_count,
)
from domain.calibration.vehicle_3d import (
    BBox2D,
    CameraIntrinsicsPrior,
    CameraMountPrior,
    HomographyConsistencyInput,
    Vehicle3DCalibrationService,
    Vehicle3DObservation,
    Vehicle3DPrior,
)
from domain.detection.service import DetectionService
from domain.zones.models import ZoneConfig
from infrastructure.cv.auto_calibration_extractor import FrameGeometryExtractor
from infrastructure.cv.supervision_adapter import SupervisionRuntimeAdapter
from infrastructure.cv.video_processor import OpenCVVideoFrameSource, SupervisionVideoProcessor
from shared.configs.settings import Settings

SEMANTIC_TRAFFIC_CLASS_IDS = {0, 1, 2, 3, 5, 7, 9, 10, 11}
VALIDATION_ERROR_TRUST_MAX_PX = 15.0
MIN_INDEPENDENT_VALIDATION_SEGMENTS = 2


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
    calibration_trusted: bool
    road_plane_polygon_world: list[tuple[float, float]] | None
    validation_segments: list[dict[str, Any]]
    notes: str
    scale_prior: dict[str, Any] | None = None
    profile_notes: str | None = None
    road_plane_polygon_pixel: list[tuple[float, float]] | None = None
    annotation_method: str | None = None
    evidence_sources: list[str] | None = None
    camera_intrinsics_prior: dict[str, Any] = field(default_factory=dict)
    camera_mount_prior: dict[str, Any] = field(default_factory=dict)
    vehicle_3d_priors: dict[str, Any] = field(default_factory=dict)
    vehicle_3d_observations: list[dict[str, Any]] = field(default_factory=list)
    calibration_3d_diagnostics: dict[str, Any] = field(default_factory=dict)
    metric_planes: list[dict[str, Any]] = field(default_factory=list)


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
    calibration_trusted: bool
    road_plane_polygon_world: list[tuple[float, float]] | None
    validation_segments: list[dict[str, Any]]
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
    road_plane_polygon_pixel: list[tuple[float, float]] | None = None
    annotation_method: str | None = None
    evidence_sources: list[str] | None = None
    camera_intrinsics_prior: dict[str, Any] = field(default_factory=dict)
    camera_mount_prior: dict[str, Any] = field(default_factory=dict)
    vehicle_3d_priors: dict[str, Any] = field(default_factory=dict)
    vehicle_3d_observations: list[dict[str, Any]] = field(default_factory=list)
    calibration_3d_diagnostics: dict[str, Any] = field(default_factory=dict)
    metric_planes: list[dict[str, Any]] = field(default_factory=list)


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


def _parse_world_polygon(value: Any) -> list[tuple[float, float]] | None:
    if not isinstance(value, list):
        return None
    polygon: list[tuple[float, float]] = []
    for point in value:
        if not isinstance(point, (list, tuple)) or len(point) != 2:
            return None
        polygon.append((float(point[0]), float(point[1])))
    return polygon if len(polygon) >= 3 else None


def _parse_validation_segments(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [dict(segment) for segment in value if isinstance(segment, dict)]


def _optional_float(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float, str)):
        return float(value)
    return None


def _parse_camera_intrinsics_prior(value: dict[str, Any]) -> CameraIntrinsicsPrior:
    raw_bounds = value.get("fx_bounds_scale", [0.5, 2.0])
    bounds = (
        raw_bounds
        if isinstance(raw_bounds, list) and len(raw_bounds) >= 2
        else [0.5, 2.0]
    )
    raw_dist = value.get("dist_coeffs", [0.0, 0.0, 0.0, 0.0, 0.0])
    dist_values = raw_dist if isinstance(raw_dist, list) else []
    padded_dist = [*dist_values, 0.0, 0.0, 0.0, 0.0, 0.0][:5]
    return CameraIntrinsicsPrior(
        fx=_optional_float(value.get("fx")),
        fy=_optional_float(value.get("fy")),
        cx=_optional_float(value.get("cx")),
        cy=_optional_float(value.get("cy")),
        fov_deg=_optional_float(value.get("fov_deg")),
        dist_coeffs=(
            float(padded_dist[0]),
            float(padded_dist[1]),
            float(padded_dist[2]),
            float(padded_dist[3]),
            float(padded_dist[4]),
        ),
        fx_bounds_scale=(float(bounds[0]), float(bounds[1])),
        source=str(value.get("source", "profile_prior")),
        confidence=float(value.get("confidence", 0.7)),
    )


def _parse_camera_mount_prior(value: dict[str, Any]) -> CameraMountPrior:
    return CameraMountPrior(
        height_m=float(value["height_m"]),
        pitch_deg=_optional_float(value.get("pitch_deg")),
        roll_deg=_optional_float(value.get("roll_deg")),
        yaw_deg=_optional_float(value.get("yaw_deg")),
        height_sigma_m=float(value.get("height_sigma_m", 1.0)),
        source=str(value.get("source", "profile_prior")),
    )


def _parse_vehicle_3d_prior(value: dict[str, Any]) -> Vehicle3DPrior:
    return Vehicle3DPrior(
        length_m=float(value["length_m"]),
        width_m=float(value["width_m"]),
        height_m=float(value["height_m"]),
        length_sigma_m=float(value.get("length_sigma_m", 0.3)),
        width_sigma_m=float(value.get("width_sigma_m", 0.2)),
        height_sigma_m=float(value.get("height_sigma_m", 0.2)),
    )


def _parse_vehicle_3d_observation(value: dict[str, Any]) -> Vehicle3DObservation:
    bbox = value["bbox_xyxy"]
    raw_keypoints = value.get("optional_keypoints")
    optional_keypoints = list(raw_keypoints) if isinstance(raw_keypoints, list) else []
    return Vehicle3DObservation(
        class_name=str(value["class_name"]),
        bbox=BBox2D(
            left=float(bbox[0]),
            top=float(bbox[1]),
            right=float(bbox[2]),
            bottom=float(bbox[3]),
        ),
        frame_index=int(value["frame_index"]),
        lane_direction_deg=float(value["lane_direction_deg"]),
        estimated_heading_deg=_optional_float(value.get("estimated_heading_deg")),
        optional_keypoints=optional_keypoints,
    )


def build_vehicle_3d_diagnostics(
    *,
    frame_width: int,
    frame_height: int,
    camera_intrinsics_prior: dict[str, Any],
    camera_mount_prior: dict[str, Any],
    vehicle_3d_priors: dict[str, Any],
    vehicle_3d_observations: list[dict[str, Any]],
    manual_pixel_to_world_h: np.ndarray | None = None,
    world_width_m: float | None = None,
    world_length_m: float | None = None,
    speed_delta_kmh: float | None = None,
) -> dict[str, object]:
    if (
        not camera_intrinsics_prior
        or not camera_mount_prior
        or not vehicle_3d_priors
        or not vehicle_3d_observations
    ):
        return {}
    priors = {
        str(name): _parse_vehicle_3d_prior(value)
        for name, value in vehicle_3d_priors.items()
        if isinstance(value, dict)
    }
    observations = [
        _parse_vehicle_3d_observation(value)
        for value in vehicle_3d_observations
        if isinstance(value, dict)
    ]
    if not priors or not observations:
        return {}
    service = Vehicle3DCalibrationService()
    first_pass = service.estimate_from_bbox_priors(
        frame_width=frame_width,
        frame_height=frame_height,
        intrinsics_prior=_parse_camera_intrinsics_prior(camera_intrinsics_prior),
        mount_prior=_parse_camera_mount_prior(camera_mount_prior),
        vehicle_priors=priors,
        observations=observations,
    )
    consistency = _vehicle_3d_homography_consistency_input(
        manual_pixel_to_world_h=manual_pixel_to_world_h,
        candidate_h_world_to_pixel=first_pass.h_world_to_pixel,
        world_width_m=world_width_m,
        world_length_m=world_length_m,
        speed_delta_kmh=speed_delta_kmh,
    )
    if consistency is None:
        return first_pass.to_dict()
    return service.estimate_from_bbox_priors(
        frame_width=frame_width,
        frame_height=frame_height,
        intrinsics_prior=_parse_camera_intrinsics_prior(camera_intrinsics_prior),
        mount_prior=_parse_camera_mount_prior(camera_mount_prior),
        vehicle_priors=priors,
        observations=observations,
        homography_consistency=consistency,
    ).to_dict()


def _vehicle_3d_homography_consistency_input(
    *,
    manual_pixel_to_world_h: np.ndarray | None,
    candidate_h_world_to_pixel: object,
    world_width_m: float | None,
    world_length_m: float | None,
    speed_delta_kmh: float | None,
) -> HomographyConsistencyInput | None:
    if (
        manual_pixel_to_world_h is None
        or candidate_h_world_to_pixel is None
        or world_width_m is None
        or world_length_m is None
        or world_width_m <= 0
        or world_length_m <= 0
    ):
        return None
    candidate = np.array(candidate_h_world_to_pixel, dtype=np.float64)
    manual_world_to_pixel_h = np.linalg.inv(manual_pixel_to_world_h).astype(np.float64)
    world_corners = np.array(
        [
            [0.0, 0.0, 1.0],
            [world_width_m, 0.0, 1.0],
            [world_width_m, world_length_m, 1.0],
            [0.0, world_length_m, 1.0],
        ],
        dtype=np.float64,
    )
    manual_pixels = (manual_world_to_pixel_h @ world_corners.T).T
    candidate_pixels = (candidate @ world_corners.T).T
    manual_pixels = manual_pixels[:, :2] / manual_pixels[:, 2:3]
    candidate_pixels = candidate_pixels[:, :2] / candidate_pixels[:, 2:3]
    deltas = np.linalg.norm(manual_pixels - candidate_pixels, axis=1)
    return HomographyConsistencyInput(
        world_to_pixel_rmse_delta_px=float(np.sqrt(np.mean(deltas**2))),
        grid_corner_mean_shift_px=float(np.mean(deltas)),
        speed_delta_kmh=speed_delta_kmh,
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
            calibration_trusted=bool(value.get("calibration_trusted", False)),
            road_plane_polygon_world=_parse_world_polygon(
                value.get("road_plane_polygon_world"),
            ),
            road_plane_polygon_pixel=_parse_world_polygon(
                value.get("road_plane_polygon_pixel"),
            ),
            validation_segments=_parse_validation_segments(
                value.get("validation_segments"),
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
            annotation_method=value.get("annotation_method"),
            evidence_sources=[
                str(source) for source in value.get("evidence_sources", [])
            ]
            if isinstance(value.get("evidence_sources"), list)
            else [],
            camera_intrinsics_prior=dict(value.get("camera_intrinsics_prior", {})),
            camera_mount_prior=dict(value.get("camera_mount_prior", {})),
            vehicle_3d_priors=dict(value.get("vehicle_3d_priors", {})),
            vehicle_3d_observations=list(value.get("vehicle_3d_observations", [])),
            calibration_3d_diagnostics=dict(value.get("calibration_3d_diagnostics", {})),
            metric_planes=list(value.get("metric_planes", []))
            if isinstance(value.get("metric_planes"), list)
            else [],
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
            calibration_trusted=bool(value.get("calibration_trusted", False)),
            scale_prior=dict(value["scale_prior"])
            if isinstance(value.get("scale_prior"), dict)
            else None,
            profile_notes=str(value.get("profile_notes", ""))
            if value.get("profile_notes") is not None
            else None,
            road_plane_polygon_pixel=_parse_world_polygon(
                value.get("road_plane_polygon_pixel"),
            ),
            road_plane_polygon_world=_parse_world_polygon(
                value.get("road_plane_polygon_world"),
            ),
            validation_segments=_parse_validation_segments(
                value.get("validation_segments"),
            ),
            notes=value.get("notes", ""),
            annotation_method=value.get("annotation_method"),
            evidence_sources=[
                str(source) for source in value.get("evidence_sources", [])
            ]
            if isinstance(value.get("evidence_sources"), list)
            else [],
            camera_intrinsics_prior=dict(value.get("camera_intrinsics_prior", {})),
            camera_mount_prior=dict(value.get("camera_mount_prior", {})),
            vehicle_3d_priors=dict(value.get("vehicle_3d_priors", {})),
            vehicle_3d_observations=list(value.get("vehicle_3d_observations", [])),
            calibration_3d_diagnostics=dict(value.get("calibration_3d_diagnostics", {})),
            metric_planes=list(value.get("metric_planes", []))
            if isinstance(value.get("metric_planes"), list)
            else [],
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


def validation_segment_max_error_px(
    calibration: HomographyResult,
    validation_segments: list[dict[str, Any]],
) -> float | None:
    errors: list[float] = []
    inverse_h = np.linalg.inv(calibration.homography_matrix).astype(np.float64)
    for segment in validation_segments:
        for pixel_key, world_key in (
            ("pixel_start", "world_start"),
            ("pixel_end", "world_end"),
        ):
            pixel_value = segment.get(pixel_key)
            world_value = segment.get(world_key)
            if (
                not isinstance(pixel_value, (list, tuple))
                or len(pixel_value) != 2
                or not isinstance(world_value, (list, tuple))
                or len(world_value) != 2
            ):
                continue
            projected = inverse_h @ np.array(
                [float(world_value[0]), float(world_value[1]), 1.0],
                dtype=float,
            )
            projected = projected / projected[2]
            expected = np.array([float(pixel_value[0]), float(pixel_value[1])], dtype=float)
            errors.append(float(np.linalg.norm(projected[:2] - expected)))
    return max(errors) if errors else None


def is_trusted_manual_calibration(
    calibration: HomographyResult,
    calibration_source: str,
    declared_trusted: bool,
    validation_max_error_px: float | None,
    independent_validation_segment_count: int,
    annotation_method: str | None = None,
    evidence_sources: list[str] | None = None,
    scale_prior: dict[str, Any] | str | None = None,
) -> bool:
    if calibration_source not in {"video_manual_preset", "camera_manual_preset"}:
        return False
    if not declared_trusted or calibration.calibration_quality == "unstable":
        return False
    if manual_calibration_provenance_issues(
        annotation_method=annotation_method,
        evidence_sources=evidence_sources,
        scale_prior=scale_prior,
    ):
        return False
    if validation_max_error_px is None:
        return False
    if independent_validation_segment_count < MIN_INDEPENDENT_VALIDATION_SEGMENTS:
        return False
    return validation_max_error_px <= VALIDATION_ERROR_TRUST_MAX_PX


def calibration_notes(
    calibration_source: str,
    video_preset: VideoCalibrationPreset | None,
    camera_profile: CameraProfilePreset | None,
    profile: SceneProfile,
) -> str:
    if calibration_source == "video_manual_preset" and video_preset is not None:
        return video_preset.notes
    if calibration_source == "camera_manual_preset" and camera_profile is not None:
        return camera_profile.fallback_policy
    return profile.notes


def profile_reuse_note(
    calibration_source: str,
    camera_profile: CameraProfilePreset | None,
) -> str | None:
    if calibration_source == "video_manual_preset" and camera_profile is not None:
        return (
            "exact video calibration overrides matching fixed-camera profile; "
            "camera profile supplies zones and tuning only"
        )
    if calibration_source == "camera_manual_preset" and camera_profile is not None:
        return "fixed camera calibration reused by filename pattern"
    return None


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
    settings = Settings()
    metadata = inspect_video(path)
    profile = profile_for_clip(path, presets.scene_profiles)
    camera_profile = match_camera_profile(path, presets.camera_profiles)
    video_preset = presets.video_calibrations.get(path.name)
    use_video_manual = video_preset is not None
    auto_diagnostics = None
    frame_geometry_evidence = None
    if camera_profile is not None:
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
    if use_video_manual:
        calibration = build_calibration(
            metadata["width"],
            metadata["height"],
            profile,
            video_preset,
        )
        zone = (
            build_camera_profile_zone(metadata["width"], metadata["height"], camera_profile)
            if camera_profile is not None
            else build_zone(metadata["width"], metadata["height"], profile)
        )
    elif camera_profile is not None:
        calibration = build_camera_profile_calibration(camera_profile)
        zone = build_camera_profile_zone(
            metadata["width"],
            metadata["height"],
            camera_profile,
        )
    else:
        calibration = build_calibration(
            metadata["width"],
            metadata["height"],
            profile,
            video_preset,
        )
        zone = build_zone(metadata["width"], metadata["height"], profile)
    calibration_source = (
        "video_manual_preset"
        if use_video_manual
        else "camera_manual_preset"
        if camera_profile is not None
        else "scene_profile_preset"
    )
    declared_calibration_trusted = (
        video_preset.calibration_trusted
        if video_preset is not None
        else camera_profile.calibration_trusted
        if camera_profile is not None
        else False
    )
    road_plane_polygon_world = (
        video_preset.road_plane_polygon_world
        if video_preset is not None
        else camera_profile.road_plane_polygon_world
        if camera_profile is not None
        else None
    )
    road_plane_polygon_pixel = (
        video_preset.road_plane_polygon_pixel
        if video_preset is not None
        else camera_profile.road_plane_polygon_pixel
        if camera_profile is not None
        else None
    )
    validation_segments = (
        video_preset.validation_segments
        if video_preset is not None
        else camera_profile.validation_segments
        if camera_profile is not None
        else []
    )
    calibration_annotation_method = (
        video_preset.annotation_method
        if video_preset is not None
        else camera_profile.annotation_method
        if camera_profile is not None
        else None
    )
    calibration_evidence_sources = (
        video_preset.evidence_sources
        if video_preset is not None
        else camera_profile.evidence_sources
        if camera_profile is not None
        else []
    )
    calibration_scale_prior = (
        video_preset.scale_prior
        if video_preset is not None
        else camera_profile.scale_prior_used
        if camera_profile is not None
        else None
    )
    provenance_issues = manual_calibration_provenance_issues(
        annotation_method=calibration_annotation_method,
        evidence_sources=calibration_evidence_sources,
        scale_prior=calibration_scale_prior,
    )
    validation_max_error_px = validation_segment_max_error_px(
        calibration,
        validation_segments,
    )
    calibration_points = (
        video_preset.points
        if video_preset is not None
        else camera_profile.manual_control_points
        if camera_profile is not None
        else []
    )
    metric_planes = (
        video_preset.metric_planes
        if video_preset is not None
        else camera_profile.metric_planes
        if camera_profile is not None
        else []
    )
    independent_validation_segment_count = validation_independent_segment_count(
        calibration_points,
        validation_segments,
    )
    calibration_trusted = is_trusted_manual_calibration(
        calibration,
        calibration_source,
        declared_calibration_trusted,
        validation_max_error_px,
        independent_validation_segment_count,
        calibration_annotation_method,
        calibration_evidence_sources,
        calibration_scale_prior,
    )
    rmse_floor_m = (
        video_preset.position_rmse_floor_m
        if video_preset is not None
        else camera_profile.position_rmse_floor_m
        if camera_profile is not None
        else profile.position_rmse_floor_m
    )
    scale_uncertainty_pct = (
        video_preset.calibration_scale_uncertainty_pct
        if video_preset is not None
        else camera_profile.calibration_scale_uncertainty_pct
        if camera_profile is not None
        else profile.calibration_scale_uncertainty_pct
    )
    camera_intrinsics_prior = (
        video_preset.camera_intrinsics_prior
        if video_preset is not None and video_preset.camera_intrinsics_prior
        else camera_profile.camera_intrinsics_prior
        if camera_profile is not None
        else {}
    )
    camera_mount_prior = (
        video_preset.camera_mount_prior
        if video_preset is not None and video_preset.camera_mount_prior
        else camera_profile.camera_mount_prior
        if camera_profile is not None
        else {}
    )
    vehicle_3d_priors = (
        video_preset.vehicle_3d_priors
        if video_preset is not None and video_preset.vehicle_3d_priors
        else camera_profile.vehicle_3d_priors
        if camera_profile is not None
        else {}
    )
    vehicle_3d_observations = (
        video_preset.vehicle_3d_observations
        if video_preset is not None and video_preset.vehicle_3d_observations
        else camera_profile.vehicle_3d_observations
        if camera_profile is not None
        else []
    )
    saved_calibration_3d_diagnostics = (
        video_preset.calibration_3d_diagnostics
        if video_preset is not None and video_preset.calibration_3d_diagnostics
        else camera_profile.calibration_3d_diagnostics
        if camera_profile is not None
        else {}
    )
    calibration_3d_diagnostics = build_vehicle_3d_diagnostics(
        frame_width=metadata["width"],
        frame_height=metadata["height"],
        camera_intrinsics_prior=camera_intrinsics_prior,
        camera_mount_prior=camera_mount_prior,
        vehicle_3d_priors=vehicle_3d_priors,
        vehicle_3d_observations=vehicle_3d_observations,
        manual_pixel_to_world_h=calibration.homography_matrix,
        world_width_m=camera_profile.world_width_m
        if camera_profile and not use_video_manual
        else profile.world_width_m,
        world_length_m=camera_profile.world_length_m
        if camera_profile and not use_video_manual
        else profile.world_length_m,
    ) or saved_calibration_3d_diagnostics
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
        if camera_profile and not use_video_manual
        else profile.world_width_m,
        segment_length_m=camera_profile.world_length_m
        if camera_profile and not use_video_manual
        else profile.world_length_m,
        grid_spacing_m=camera_profile.grid_spacing_m if camera_profile else 5.0,
        position_rmse_floor_m=rmse_floor_m,
        rendered_video_path=rendered_video_path,
        rendered_video_fps=max(metadata["fps"] / frame_stride, 1.0),
        trajectory_reconstruction_enabled=settings.cv.trajectory_reconstruction_enabled,
        pose_enabled=settings.cv.pose_enabled,
        pose_model_path=settings.cv.pose_model,
        pose_device=device,
        calibration_context={
            "calibration_source": calibration_source,
            "calibration_trusted": calibration_trusted,
            "declared_calibration_trusted": declared_calibration_trusted,
            "road_plane_polygon_world": road_plane_polygon_world,
            "road_plane_polygon_pixel": road_plane_polygon_pixel,
            "validation_segments": validation_segments,
            "validation_max_error_px": validation_max_error_px,
            "manual_control_point_count": len(calibration_points),
            "manual_control_points": [
                {
                    "pixel_x": point.pixel_x,
                    "pixel_y": point.pixel_y,
                    "world_x": point.world_x,
                    "world_y": point.world_y,
                }
                for point in calibration_points
            ],
            "metric_planes": metric_planes,
            "independent_validation_segment_count": independent_validation_segment_count,
            "annotation_method": calibration_annotation_method,
            "evidence_sources": calibration_evidence_sources,
            "provenance_trusted": not provenance_issues,
            "provenance_issues": provenance_issues,
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
            "camera_intrinsics_prior": camera_intrinsics_prior,
            "camera_mount_prior": camera_mount_prior,
            "vehicle_3d_priors": vehicle_3d_priors,
            "vehicle_3d_observations": vehicle_3d_observations,
            "calibration_3d_diagnostics": calibration_3d_diagnostics,
            "auto_calibration": auto_diagnostics.to_dict()
            if auto_diagnostics is not None
            else None,
            "frame_geometry_evidence": frame_geometry_evidence.to_dict()
            if frame_geometry_evidence is not None
            else None,
            "profile_reuse_note": profile_reuse_note(
                calibration_source,
                camera_profile,
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
            "source": calibration_source,
            "trusted": calibration_trusted,
            "declared_trusted": declared_calibration_trusted,
            "camera_profile_id": camera_profile.profile_id if camera_profile else None,
            "camera_profile_role": camera_profile.role if camera_profile else None,
            "quality": calibration.calibration_quality,
            "rmse": calibration.pixel_to_world_rmse_m,
            "pixel_to_world_rmse_m": calibration.pixel_to_world_rmse_m,
            "world_to_pixel_rmse_px": calibration.world_to_pixel_rmse_px,
            "validation_max_error_px": validation_max_error_px,
            "independent_validation_segment_count": independent_validation_segment_count,
            "annotation_method": calibration_annotation_method,
            "evidence_sources": calibration_evidence_sources,
            "provenance_trusted": not provenance_issues,
            "provenance_issues": provenance_issues,
            "inlier_count": calibration.inlier_count,
            "position_rmse_floor_m": rmse_floor_m,
            "scale_uncertainty_pct": scale_uncertainty_pct,
            "notes": calibration_notes(
                calibration_source,
                video_preset,
                camera_profile,
                profile,
            ),
            "auto_calibration": auto_diagnostics.to_dict()
            if auto_diagnostics is not None
            else None,
            "frame_geometry_evidence": frame_geometry_evidence.to_dict()
            if frame_geometry_evidence is not None
            else None,
            "calibration_3d_diagnostics": calibration_3d_diagnostics,
        },
        "processed_video": {
            "path": str(rendered_video_path) if rendered_video_path is not None else None,
            "filename": rendered_video_path.name if rendered_video_path is not None else None,
        },
        "sensitivity": sensitivity,
        "final_report": report
        | {
            "calibration_diagnostics": (report.get("calibration_diagnostics") or {})
            | {
                "homography_model": "RANSAC planar homography, pixel(u,v) -> ground(X,Y)",
                "calibration_source": calibration_source,
                "calibration_trusted": calibration_trusted,
                "declared_calibration_trusted": declared_calibration_trusted,
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
                "profile_reuse_note": profile_reuse_note(
                    calibration_source,
                    camera_profile,
                ),
                "auto_calibration": auto_diagnostics.to_dict()
                if auto_diagnostics is not None
                else None,
                "frame_geometry_evidence": frame_geometry_evidence.to_dict()
                if frame_geometry_evidence is not None
                else None,
                "calibration_quality": calibration.calibration_quality,
                "pixel_to_world_rmse_m": calibration.pixel_to_world_rmse_m,
                "world_to_pixel_rmse_px": calibration.world_to_pixel_rmse_px,
                "reprojection_rmse_px": calibration.world_to_pixel_rmse_px,
                "validation_max_error_px": validation_max_error_px,
                "independent_validation_segment_count": independent_validation_segment_count,
                "camera_intrinsics_prior": camera_intrinsics_prior,
                "camera_mount_prior": camera_mount_prior,
                "vehicle_3d_priors": vehicle_3d_priors,
                "vehicle_3d_observations": vehicle_3d_observations,
                "calibration_3d_diagnostics": calibration_3d_diagnostics,
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
                    *(
                        []
                        if independent_validation_segment_count
                        >= MIN_INDEPENDENT_VALIDATION_SEGMENTS
                        else ["validation_segments_reuse_control_points"]
                    ),
                    *(["non_manual_or_visual_prior_calibration"] if provenance_issues else []),
                    *([] if calibration_trusted else ["untrusted_calibration_grid_suppressed"]),
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
