from __future__ import annotations

from dataclasses import dataclass

import numpy as np

RAW_DISTORTED_PIXEL = "raw_distorted_pixel"
UNDISTORTED_PIXEL = "undistorted_pixel"
NORMALIZED_CAMERA_RAY = "normalized_camera_ray"
GROUND_WORLD_METER = "ground_world_meter"


@dataclass(frozen=True)
class CoordinateTransformResult:
    pixel: tuple[float, float] | None
    input_space: str
    output_space: str
    rectification_applied: bool
    gate_reason: str | None = None


@dataclass(frozen=True)
class CoordinateSpaceContract:
    image_coordinate_space: str
    homography_coordinate_space: str
    control_point_coordinate_space: str
    frame_size: tuple[int, int] | None
    camera_matrix_used: list[list[float]] | None
    new_camera_matrix_used: list[list[float]] | None
    distortion_model_source: str | None
    distortion_coefficients: list[float] | None
    rectification_applied: bool
    gate_reason: str | None = None

    @classmethod
    def from_context(
        cls,
        context: dict[str, object],
        *,
        frame_width: int,
        frame_height: int,
    ) -> CoordinateSpaceContract:
        homography_space = _canonical_space(
            context.get("homography_coordinate_space"),
            default=RAW_DISTORTED_PIXEL,
        )
        image_space = _canonical_space(
            context.get("image_coordinate_space"),
            default=RAW_DISTORTED_PIXEL,
        )
        control_space = _canonical_space(
            context.get("control_point_coordinate_space"),
            default=homography_space,
        )
        camera_matrix = _matrix3(context.get("camera_matrix_used")) or _matrix3(
            context.get("camera_intrinsics"),
        )
        new_camera_matrix = _matrix3(context.get("new_camera_matrix_used")) or _matrix3(
            context.get("new_camera_matrix"),
        )
        distortion = _distortion_coefficients(context.get("distortion_coefficients"))
        distortion_source = (
            str(context.get("distortion_model_source"))
            if context.get("distortion_model_source") is not None
            else ("camera_profile" if distortion is not None else None)
        )
        rectification_applied = bool(context.get("rectification_applied", False))
        gate_reason = None
        if homography_space == UNDISTORTED_PIXEL:
            if camera_matrix is None or distortion is None:
                gate_reason = "distortion_model_missing"
            elif control_space != UNDISTORTED_PIXEL:
                gate_reason = "undistorted_homography_requires_undistorted_points"
        elif homography_space == RAW_DISTORTED_PIXEL and rectification_applied:
            gate_reason = "raw_homography_reused_after_undistort"
        elif image_space != homography_space and homography_space != UNDISTORTED_PIXEL:
            gate_reason = "coordinate_space_mismatch"
        return cls(
            image_coordinate_space=image_space,
            homography_coordinate_space=homography_space,
            control_point_coordinate_space=control_space,
            frame_size=(int(frame_width), int(frame_height)),
            camera_matrix_used=camera_matrix,
            new_camera_matrix_used=new_camera_matrix,
            distortion_model_source=distortion_source,
            distortion_coefficients=distortion,
            rectification_applied=rectification_applied,
            gate_reason=gate_reason,
        )

    def transform_pixel(
        self,
        pixel: tuple[float, float],
        *,
        input_space: str = RAW_DISTORTED_PIXEL,
    ) -> CoordinateTransformResult:
        input_space = _canonical_space(input_space, default=RAW_DISTORTED_PIXEL)
        output_space = self.homography_coordinate_space
        if input_space == output_space:
            return CoordinateTransformResult(
                pixel=pixel,
                input_space=input_space,
                output_space=output_space,
                rectification_applied=False,
            )
        if output_space != UNDISTORTED_PIXEL or input_space != RAW_DISTORTED_PIXEL:
            return CoordinateTransformResult(
                pixel=None,
                input_space=input_space,
                output_space=output_space,
                rectification_applied=False,
                gate_reason="coordinate_space_mismatch",
            )
        if self.camera_matrix_used is None or self.distortion_coefficients is None:
            return CoordinateTransformResult(
                pixel=None,
                input_space=input_space,
                output_space=output_space,
                rectification_applied=False,
                gate_reason="distortion_model_missing",
            )
        try:
            import cv2  # type: ignore[import-not-found]
        except ImportError:
            return CoordinateTransformResult(
                pixel=None,
                input_space=input_space,
                output_space=output_space,
                rectification_applied=False,
                gate_reason="distortion_model_missing",
            )
        camera_matrix = np.asarray(self.camera_matrix_used, dtype=np.float64)
        new_camera_matrix = np.asarray(
            self.new_camera_matrix_used or self.camera_matrix_used,
            dtype=np.float64,
        )
        coefficients = np.asarray(self.distortion_coefficients, dtype=np.float64)
        points = np.asarray([[pixel]], dtype=np.float64)
        undistorted = cv2.undistortPoints(
            points,
            camera_matrix,
            coefficients,
            P=new_camera_matrix,
        )
        return CoordinateTransformResult(
            pixel=(float(undistorted[0, 0, 0]), float(undistorted[0, 0, 1])),
            input_space=input_space,
            output_space=output_space,
            rectification_applied=True,
        )

    def distortion_diagnostics(self) -> dict[str, object]:
        coefficients = self.distortion_coefficients or []
        distortion_strength = float(max((abs(value) for value in coefficients), default=0.0))
        return {
            "distortion_model_source": self.distortion_model_source,
            "distortion_coefficient_count": len(coefficients),
            "distortion_strength": distortion_strength,
            "camera_matrix_available": self.camera_matrix_used is not None,
            "new_camera_matrix_available": self.new_camera_matrix_used is not None,
            "model_reference": "camera_distortion_coordinate_contract_v1",
        }

    def to_diagnostics(self) -> dict[str, object]:
        return {
            "image_coordinate_space": self.image_coordinate_space,
            "homography_coordinate_space": self.homography_coordinate_space,
            "control_point_coordinate_space": self.control_point_coordinate_space,
            "frame_size": list(self.frame_size) if self.frame_size is not None else None,
            "camera_matrix_used": self.camera_matrix_used,
            "new_camera_matrix_used": self.new_camera_matrix_used,
            "distortion_model_source": self.distortion_model_source,
            "rectification_applied": self.rectification_applied,
            "gate_reason": self.gate_reason,
            "model_reference": "image_coordinate_space_contract_v1",
        }


@dataclass(frozen=True)
class CameraGeometryProfile:
    profile_id: str | None
    frame_size: tuple[int, int] | None
    coordinate_contract: CoordinateSpaceContract
    metric_planes: list[dict[str, object]]
    validation_metrics: dict[str, object]
    pinhole_geometry_profile: dict[str, object] | None = None

    @classmethod
    def from_context(
        cls,
        context: dict[str, object],
        *,
        frame_width: int,
        frame_height: int,
        coordinate_contract: CoordinateSpaceContract,
        metric_planes: list[dict[str, object]],
        validation_metrics: dict[str, object],
        pinhole_geometry_profile: dict[str, object] | None = None,
    ) -> CameraGeometryProfile:
        profile_id = context.get("camera_geometry_profile_id") or context.get(
            "camera_profile_id",
        )
        return cls(
            profile_id=str(profile_id) if profile_id is not None else None,
            frame_size=(int(frame_width), int(frame_height)),
            coordinate_contract=coordinate_contract,
            metric_planes=metric_planes,
            validation_metrics=validation_metrics,
            pinhole_geometry_profile=pinhole_geometry_profile,
        )

    @property
    def homography_coordinate_space(self) -> str:
        return self.coordinate_contract.homography_coordinate_space

    @property
    def point_coordinate_space(self) -> str:
        return self.coordinate_contract.image_coordinate_space

    @property
    def gate_reason(self) -> str | None:
        return self.coordinate_contract.gate_reason

    def to_diagnostics(self) -> dict[str, object]:
        return {
            "camera_geometry_profile_id": self.profile_id,
            "frame_size": list(self.frame_size) if self.frame_size is not None else None,
            "homography_coordinate_space": self.homography_coordinate_space,
            "point_coordinate_space": self.point_coordinate_space,
            "control_point_coordinate_space": (
                self.coordinate_contract.control_point_coordinate_space
            ),
            "rectification_applied": self.coordinate_contract.rectification_applied,
            "coordinate_space_gate_reason": self.gate_reason,
            "metric_plane_count": len(self.metric_planes),
            "metric_plane_ids": [
                str(plane.get("plane_id"))
                for plane in self.metric_planes
                if plane.get("plane_id") is not None
            ],
            "validation_metrics": dict(self.validation_metrics),
            "pinhole_geometry_profile": self.pinhole_geometry_profile,
            "model_reference": "camera_geometry_profile_v1",
        }


def _canonical_space(value: object, *, default: str) -> str:
    text = str(value or default).strip()
    aliases = {
        "raw_frame": RAW_DISTORTED_PIXEL,
        "raw_pixel": RAW_DISTORTED_PIXEL,
        "distorted_pixel": RAW_DISTORTED_PIXEL,
        "undistorted_frame": UNDISTORTED_PIXEL,
        "undistorted": UNDISTORTED_PIXEL,
        "normalized": NORMALIZED_CAMERA_RAY,
        "world": GROUND_WORLD_METER,
    }
    return aliases.get(text, text)


def _matrix3(value: object) -> list[list[float]] | None:
    if isinstance(value, dict):
        try:
            fx = float(value["fx"])
            fy = float(value["fy"])
            cx = float(value["cx"])
            cy = float(value["cy"])
        except (KeyError, TypeError, ValueError):
            return None
        return [[fx, 0.0, cx], [0.0, fy, cy], [0.0, 0.0, 1.0]]
    if not isinstance(value, list) or len(value) != 3:
        return None
    matrix: list[list[float]] = []
    for row in value:
        if not isinstance(row, list) or len(row) != 3:
            return None
        try:
            matrix.append([float(item) for item in row])
        except (TypeError, ValueError):
            return None
    return matrix


def _distortion_coefficients(value: object) -> list[float] | None:
    if isinstance(value, dict):
        ordered = [value.get(key) for key in ("k1", "k2", "p1", "p2", "k3")]
        if all(item is None for item in ordered):
            return None
        try:
            return [float(item or 0.0) for item in ordered]
        except (TypeError, ValueError):
            return None
    if not isinstance(value, list):
        return None
    try:
        return [float(item) for item in value]
    except (TypeError, ValueError):
        return None
