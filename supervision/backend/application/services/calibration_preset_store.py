from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import numpy as np
import yaml
from domain.calibration.models import CalibrationPoint
from domain.calibration.service import CalibrationService
from domain.calibration.validation import (
    manual_calibration_provenance_issues,
    validation_independent_segment_count,
)
from domain.calibration.vehicle_3d import (
    BBox2D,
    CameraIntrinsicsPrior,
    CameraMountPrior,
    Vehicle3DCalibrationService,
    Vehicle3DObservation,
    Vehicle3DPrior,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CALIBRATION_PRESET_PATH = PROJECT_ROOT / "data/tests/calibration_presets.yaml"
VALIDATION_ERROR_TRUST_MAX_PX = 15.0
MIN_INDEPENDENT_VALIDATION_SEGMENTS = 2


class CalibrationPresetStore:
    def __init__(self, path: Path = DEFAULT_CALIBRATION_PRESET_PATH) -> None:
        self.path = path
        self._service = CalibrationService()

    def list_entries(self) -> dict[str, Any]:
        payload = self._load_payload()
        return {
            "preset_path": str(self.path),
            "scene_profiles": payload.get("scene_profiles", {}),
            "video_calibrations": payload.get("video_calibrations", {}),
        }

    def get_entry(self, clip_name: str) -> dict[str, Any] | None:
        calibrations = self._load_payload().get("video_calibrations", {})
        entry = calibrations.get(self._safe_clip_name(clip_name))
        return deepcopy(entry) if isinstance(entry, dict) else None

    def upsert_entry(
        self,
        clip_name: str,
        entry: dict[str, Any],
        *,
        frame_width: int | None = None,
        frame_height: int | None = None,
        grid_spacing_m: float = 5.0,
    ) -> dict[str, Any]:
        safe_clip_name = self._safe_clip_name(clip_name)
        normalized_entry = self._normalize_entry(entry)
        diagnostics = self.validate_entry(
            normalized_entry,
            frame_width=frame_width,
            frame_height=frame_height,
            grid_spacing_m=grid_spacing_m,
        )
        normalized_entry["calibration_trusted"] = bool(
            diagnostics["calibration_trusted"],
        )
        if "calibration_3d_diagnostics" in diagnostics:
            normalized_entry["calibration_3d_diagnostics"] = diagnostics[
                "calibration_3d_diagnostics"
            ]
        payload = self._load_payload()
        calibrations = payload.setdefault("video_calibrations", {})
        calibrations[safe_clip_name] = normalized_entry
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        return {
            "clip_name": safe_clip_name,
            "source": "video_manual_preset",
            "entry": normalized_entry,
            "diagnostics": diagnostics,
            "preset_path": str(self.path),
        }

    def validate_entry(
        self,
        entry: dict[str, Any],
        *,
        frame_width: int | None = None,
        frame_height: int | None = None,
        grid_spacing_m: float = 5.0,
    ) -> dict[str, Any]:
        normalized_entry = self._normalize_entry(entry)
        points = [
            CalibrationPoint(
                pixel_x=point["pixel_x"],
                pixel_y=point["pixel_y"],
                world_x=point["world_x"],
                world_y=point["world_y"],
            )
            for point in normalized_entry["points"]
        ]
        homography = self._service.compute_homography_ransac(points, random_seed=11)
        validation_max_error_px = self._validation_segment_max_error_px(
            homography.homography_matrix,
            normalized_entry["validation_segments"],
        )
        independent_validation_segment_count = validation_independent_segment_count(
            points,
            normalized_entry["validation_segments"],
        )
        provenance_issues = manual_calibration_provenance_issues(
            annotation_method=normalized_entry.get("annotation_method"),
            evidence_sources=normalized_entry.get("evidence_sources", []),
            scale_prior=normalized_entry.get("scale_prior"),
        )
        calibration_trusted = self._is_entry_trusted(
            normalized_entry,
            homography.calibration_quality,
            validation_max_error_px,
            independent_validation_segment_count,
            provenance_issues,
        )
        world_xs = [point.world_x for point in points]
        world_ys = [point.world_y for point in points]
        world_width_m = max(world_xs) - min(world_xs)
        world_length_m = max(world_ys) - min(world_ys)
        diagnostics: dict[str, Any] = {
            "homography_model": "RANSAC planar homography, pixel(u,v) -> ground(X,Y)",
            "calibration_source": "video_manual_preset",
            "declared_calibration_trusted": bool(
                normalized_entry.get("calibration_trusted", False),
            ),
            "calibration_trusted": calibration_trusted,
            "annotation_method": normalized_entry.get("annotation_method"),
            "annotation_confidence": normalized_entry.get("annotation_confidence"),
            "evidence_sources": normalized_entry.get("evidence_sources", []),
            "provenance_trusted": not provenance_issues,
            "provenance_issues": provenance_issues,
            "calibration_quality": homography.calibration_quality,
            "pixel_to_world_rmse_m": homography.pixel_to_world_rmse_m,
            "world_to_pixel_rmse_px": homography.world_to_pixel_rmse_px,
            "reprojection_rmse_px": homography.world_to_pixel_rmse_px,
            "validation_max_error_px": validation_max_error_px,
            "independent_validation_segment_count": independent_validation_segment_count,
            "validation_segments_independent": (
                independent_validation_segment_count
                >= MIN_INDEPENDENT_VALIDATION_SEGMENTS
            ),
            "inlier_count": homography.inlier_count,
            "condition_number": homography.condition_number,
            "inlier_mask": homography.inlier_mask,
            "position_rmse_m": normalized_entry["position_rmse_floor_m"],
            "scale_uncertainty_pct": normalized_entry["calibration_scale_uncertainty_pct"],
            "world_width_m": world_width_m,
            "world_length_m": world_length_m,
            "error_sources": self._error_sources(
                calibration_trusted,
                independent_validation_segment_count,
            ),
            "model_reference": "Model 1 + Model 6",
        }
        calibration_3d_diagnostics = self._vehicle_3d_diagnostics(
            normalized_entry,
            frame_width=frame_width,
            frame_height=frame_height,
        )
        if calibration_3d_diagnostics is not None:
            diagnostics["calibration_3d_diagnostics"] = calibration_3d_diagnostics
        if (
            calibration_trusted
            and frame_width
            and frame_height
            and world_width_m > 0
            and world_length_m > 0
        ):
            grid = self._service.build_homography_grid(
                homography,
                frame_width=frame_width,
                frame_height=frame_height,
                world_width_m=world_width_m,
                world_length_m=world_length_m,
                spacing_m=grid_spacing_m,
                calibration_source="video_manual_preset",
                calibration_trusted=True,
                road_plane_polygon_world=self._parse_world_polygon(
                    normalized_entry.get("road_plane_polygon_world"),
                ),
                validation_max_error_px=validation_max_error_px,
            )
            diagnostics["homography_grid"] = grid.to_dict()
        return diagnostics

    def _load_payload(self) -> dict[str, Any]:
        if not self.path.exists():
            return {
                "schema_version": 1,
                "notes": "Generated by TrafficPerceptionEngine calibration workbench.",
                "scene_profiles": {},
                "video_calibrations": {},
            }
        payload = yaml.safe_load(self.path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}

    @staticmethod
    def _normalize_entry(entry: dict[str, Any]) -> dict[str, Any]:
        points = entry.get("points")
        if not isinstance(points, list):
            raise ValueError("points must be a list")
        normalized_points: list[dict[str, float]] = []
        for point in points:
            if not isinstance(point, dict):
                raise ValueError("each calibration point must be an object")
            normalized_points.append(
                {
                    "pixel_x": float(point["pixel_x"]),
                    "pixel_y": float(point["pixel_y"]),
                    "world_x": float(point["world_x"]),
                    "world_y": float(point["world_y"]),
                },
            )
        return {
            "notes": str(entry.get("notes", "Manual calibration from frontend workbench.")),
            "position_rmse_floor_m": float(entry.get("position_rmse_floor_m", 1.0)),
            "calibration_scale_uncertainty_pct": float(
                entry.get("calibration_scale_uncertainty_pct", 5.0),
            ),
            "calibration_trusted": bool(entry.get("calibration_trusted", False)),
            "annotation_method": str(entry.get("annotation_method", "")),
            "annotation_confidence": float(entry.get("annotation_confidence", 0.0) or 0.0),
            "evidence_sources": deepcopy(entry.get("evidence_sources"))
            if isinstance(entry.get("evidence_sources"), list)
            else [],
            "auto_geometry": deepcopy(entry.get("auto_geometry"))
            if isinstance(entry.get("auto_geometry"), dict)
            else None,
            "scale_constraints": deepcopy(entry.get("scale_constraints"))
            if isinstance(entry.get("scale_constraints"), list)
            else [],
            "scale_prior": deepcopy(entry.get("scale_prior"))
            if isinstance(entry.get("scale_prior"), dict)
            else None,
            "profile_notes": str(entry.get("profile_notes", "")),
            "road_plane_polygon_pixel": CalibrationPresetStore._normalize_pixel_polygon(
                entry.get("road_plane_polygon_pixel"),
            ),
            "road_plane_polygon_world": CalibrationPresetStore._normalize_world_polygon(
                entry.get("road_plane_polygon_world"),
            ),
            "validation_segments": CalibrationPresetStore._normalize_validation_segments(
                entry.get("validation_segments", []),
            ),
            "camera_intrinsics_prior": deepcopy(entry.get("camera_intrinsics_prior"))
            if isinstance(entry.get("camera_intrinsics_prior"), dict)
            else {},
            "camera_mount_prior": deepcopy(entry.get("camera_mount_prior"))
            if isinstance(entry.get("camera_mount_prior"), dict)
            else {},
            "vehicle_3d_priors": deepcopy(entry.get("vehicle_3d_priors"))
            if isinstance(entry.get("vehicle_3d_priors"), dict)
            else {},
            "vehicle_3d_observations": deepcopy(entry.get("vehicle_3d_observations"))
            if isinstance(entry.get("vehicle_3d_observations"), list)
            else [],
            "calibration_3d_diagnostics": deepcopy(entry.get("calibration_3d_diagnostics"))
            if isinstance(entry.get("calibration_3d_diagnostics"), dict)
            else {},
            "points": normalized_points,
        }

    @staticmethod
    def _is_entry_trusted(
        entry: dict[str, Any],
        calibration_quality: str,
        validation_max_error_px: float | None,
        independent_validation_segment_count: int,
        provenance_issues: list[str],
    ) -> bool:
        if not bool(entry.get("calibration_trusted", False)):
            return False
        if provenance_issues:
            return False
        if calibration_quality == "unstable":
            return False
        if validation_max_error_px is None:
            return False
        if independent_validation_segment_count < MIN_INDEPENDENT_VALIDATION_SEGMENTS:
            return False
        return validation_max_error_px <= VALIDATION_ERROR_TRUST_MAX_PX

    @staticmethod
    def _error_sources(
        calibration_trusted: bool,
        independent_validation_segment_count: int,
    ) -> list[str]:
        sources = [
            "homography calibration residual",
            "manual control point uncertainty",
            "independent validation segment error",
        ]
        if independent_validation_segment_count < MIN_INDEPENDENT_VALIDATION_SEGMENTS:
            sources.append("validation_segments_reuse_control_points")
        if not calibration_trusted:
            sources.append("untrusted_calibration_grid_suppressed")
        return sources

    @staticmethod
    def _validation_segment_max_error_px(
        homography_matrix: np.ndarray,
        validation_segments: list[dict[str, Any]],
    ) -> float | None:
        errors: list[float] = []
        inverse_h = np.linalg.inv(homography_matrix).astype(np.float64)
        for segment in validation_segments:
            for pixel_key, world_key in (
                ("pixel_start", "world_start"),
                ("pixel_end", "world_end"),
            ):
                pixel_value = segment.get(pixel_key)
                world_value = segment.get(world_key)
                if (
                    not isinstance(pixel_value, list)
                    or len(pixel_value) != 2
                    or not isinstance(world_value, list)
                    or len(world_value) != 2
                ):
                    continue
                projected = inverse_h @ np.array(
                    [float(world_value[0]), float(world_value[1]), 1.0],
                    dtype=float,
                )
                projected = projected / projected[2]
                expected = np.array(
                    [float(pixel_value[0]), float(pixel_value[1])],
                    dtype=float,
                )
                errors.append(float(np.linalg.norm(projected[:2] - expected)))
        return max(errors) if errors else None

    @staticmethod
    def _normalize_world_polygon(value: object) -> list[list[float]] | None:
        polygon = CalibrationPresetStore._parse_world_polygon(value)
        return [[point[0], point[1]] for point in polygon] if polygon is not None else None

    @staticmethod
    def _normalize_pixel_polygon(value: object) -> list[list[float]] | None:
        polygon = CalibrationPresetStore._parse_world_polygon(value)
        return [[point[0], point[1]] for point in polygon] if polygon is not None else None

    @staticmethod
    def _parse_world_polygon(value: object) -> list[tuple[float, float]] | None:
        if not isinstance(value, list):
            return None
        polygon: list[tuple[float, float]] = []
        for point in value:
            if not isinstance(point, (list, tuple)) or len(point) != 2:
                return None
            polygon.append((float(point[0]), float(point[1])))
        return polygon if len(polygon) >= 3 else None

    @staticmethod
    def _normalize_validation_segments(value: object) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            return []
        normalized: list[dict[str, Any]] = []
        for segment in value:
            if isinstance(segment, dict):
                normalized.append(deepcopy(segment))
        return normalized

    @staticmethod
    def _vehicle_3d_diagnostics(
        entry: dict[str, Any],
        *,
        frame_width: int | None,
        frame_height: int | None,
    ) -> dict[str, object] | None:
        if frame_width is None or frame_height is None:
            return None
        if (
            not entry["camera_intrinsics_prior"]
            or not entry["camera_mount_prior"]
            or not entry["vehicle_3d_priors"]
            or not entry["vehicle_3d_observations"]
        ):
            return None
        intrinsics = CalibrationPresetStore._parse_camera_intrinsics_prior(
            entry["camera_intrinsics_prior"],
        )
        mount = CalibrationPresetStore._parse_camera_mount_prior(entry["camera_mount_prior"])
        priors = {
            str(name): CalibrationPresetStore._parse_vehicle_3d_prior(value)
            for name, value in entry["vehicle_3d_priors"].items()
            if isinstance(value, dict)
        }
        observations = [
            CalibrationPresetStore._parse_vehicle_3d_observation(value)
            for value in entry["vehicle_3d_observations"]
            if isinstance(value, dict)
        ]
        if not priors or not observations:
            return None
        return Vehicle3DCalibrationService().estimate_from_bbox_priors(
            frame_width=frame_width,
            frame_height=frame_height,
            intrinsics_prior=intrinsics,
            mount_prior=mount,
            vehicle_priors=priors,
            observations=observations,
        ).to_dict()

    @staticmethod
    def _parse_camera_intrinsics_prior(value: dict[str, Any]) -> CameraIntrinsicsPrior:
        bounds = value.get("fx_bounds_scale", [0.5, 2.0])
        raw_dist = value.get("dist_coeffs", [0.0, 0.0, 0.0, 0.0, 0.0])
        dist_values = raw_dist if isinstance(raw_dist, list) else []
        padded_dist = [*dist_values, 0.0, 0.0, 0.0, 0.0, 0.0][:5]
        raw_bounds = bounds if isinstance(bounds, list) and len(bounds) >= 2 else [0.5, 2.0]
        return CameraIntrinsicsPrior(
            fx=CalibrationPresetStore._optional_float(value.get("fx")),
            fy=CalibrationPresetStore._optional_float(value.get("fy")),
            cx=CalibrationPresetStore._optional_float(value.get("cx")),
            cy=CalibrationPresetStore._optional_float(value.get("cy")),
            fov_deg=CalibrationPresetStore._optional_float(value.get("fov_deg")),
            dist_coeffs=(
                float(padded_dist[0]),
                float(padded_dist[1]),
                float(padded_dist[2]),
                float(padded_dist[3]),
                float(padded_dist[4]),
            ),
            fx_bounds_scale=(float(raw_bounds[0]), float(raw_bounds[1])),
            source=str(value.get("source", "profile_prior")),
            confidence=float(value.get("confidence", 0.7)),
        )

    @staticmethod
    def _parse_camera_mount_prior(value: dict[str, Any]) -> CameraMountPrior:
        return CameraMountPrior(
            height_m=float(value["height_m"]),
            pitch_deg=CalibrationPresetStore._optional_float(value.get("pitch_deg")),
            roll_deg=CalibrationPresetStore._optional_float(value.get("roll_deg")),
            yaw_deg=CalibrationPresetStore._optional_float(value.get("yaw_deg")),
            height_sigma_m=float(value.get("height_sigma_m", 1.0)),
            source=str(value.get("source", "profile_prior")),
        )

    @staticmethod
    def _parse_vehicle_3d_prior(value: dict[str, Any]) -> Vehicle3DPrior:
        return Vehicle3DPrior(
            length_m=float(value["length_m"]),
            width_m=float(value["width_m"]),
            height_m=float(value["height_m"]),
            length_sigma_m=float(value.get("length_sigma_m", 0.3)),
            width_sigma_m=float(value.get("width_sigma_m", 0.2)),
            height_sigma_m=float(value.get("height_sigma_m", 0.2)),
        )

    @staticmethod
    def _parse_vehicle_3d_observation(value: dict[str, Any]) -> Vehicle3DObservation:
        bbox = value["bbox_xyxy"]
        raw_keypoints = value.get("optional_keypoints")
        optional_keypoints: list[dict[str, Any]] = (
            deepcopy(raw_keypoints) if isinstance(raw_keypoints, list) else []
        )
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
            estimated_heading_deg=CalibrationPresetStore._optional_float(
                value.get("estimated_heading_deg"),
            ),
            optional_keypoints=optional_keypoints,
        )

    @staticmethod
    def _optional_float(value: object) -> float | None:
        if value is None or isinstance(value, bool):
            return None
        if isinstance(value, (int, float, str)):
            return float(value)
        return None

    @staticmethod
    def _safe_clip_name(clip_name: str) -> str:
        safe_name = Path(clip_name).name
        if not safe_name.endswith(".mp4"):
            raise ValueError("clip_name must be an MP4 filename")
        return safe_name
