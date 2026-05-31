from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True)
class BBox2D:
    left: float
    top: float
    right: float
    bottom: float

    @property
    def width(self) -> float:
        return self.right - self.left

    @property
    def height(self) -> float:
        return self.bottom - self.top


@dataclass(frozen=True)
class Vehicle3DPrior:
    length_m: float
    width_m: float
    height_m: float
    length_sigma_m: float = 0.3
    width_sigma_m: float = 0.2
    height_sigma_m: float = 0.2


@dataclass(frozen=True)
class CameraIntrinsicsPrior:
    fx: float | None = None
    fy: float | None = None
    cx: float | None = None
    cy: float | None = None
    fov_deg: float | None = None
    dist_coeffs: tuple[float, float, float, float, float] = (0.0, 0.0, 0.0, 0.0, 0.0)
    fx_bounds_scale: tuple[float, float] = (0.5, 2.0)
    source: str = "profile_prior"
    confidence: float = 0.7


@dataclass(frozen=True)
class CameraMountPrior:
    height_m: float
    pitch_deg: float | None = None
    roll_deg: float | None = None
    yaw_deg: float | None = None
    height_sigma_m: float = 1.0
    source: str = "profile_prior"


@dataclass(frozen=True)
class Vehicle3DObservation:
    class_name: str
    bbox: BBox2D
    frame_index: int
    lane_direction_deg: float
    estimated_heading_deg: float | None = None
    optional_keypoints: list[dict[str, Any]] = field(default_factory=list)

    @property
    def has_explicit_3d_2d_points(self) -> bool:
        return len(self.optional_keypoints) >= 4


@dataclass(frozen=True)
class VehicleResidualWeights:
    lambda_heading: float = 0.8
    lambda_length: float = 1.0
    lambda_width: float = 1.0
    lambda_height: float = 1.2


@dataclass(frozen=True)
class IntrinsicsBoundsCheck:
    confidence: float
    intrinsic_boundary_hit: bool
    quality_issues: list[str]


@dataclass(frozen=True)
class HomographyConsistencyInput:
    world_to_pixel_rmse_delta_px: float | None
    grid_corner_mean_shift_px: float | None
    speed_delta_kmh: float | None


@dataclass(frozen=True)
class HomographyConsistencyResult:
    passed: bool
    quality_issues: list[str]


@dataclass(frozen=True)
class Vehicle3DCalibrationResult:
    calibration_source: str
    calibration_quality: str
    calibration_trusted: bool
    confidence: float
    camera_matrix: list[list[float]]
    dist_coeffs: list[float]
    residual_vector: list[float]
    residual_rmse: float
    intrinsic_boundary_hit: bool
    homography_consistency: dict[str, object] | None
    pnp_used: bool
    pnp_point_count: int
    rvec: list[float] | None
    tvec: list[float] | None
    h_world_to_pixel: list[list[float]] | None
    h_pixel_to_world: list[list[float]] | None
    quality_issues: list[str]
    model_reference: str = "vehicle_3d_prior_pnp + bbox_envelope_lm_gate"

    def to_dict(self) -> dict[str, object]:
        return {
            "calibration_source": self.calibration_source,
            "calibration_quality": self.calibration_quality,
            "calibration_trusted": self.calibration_trusted,
            "confidence": self.confidence,
            "camera_matrix": self.camera_matrix,
            "dist_coeffs": self.dist_coeffs,
            "residual_vector": self.residual_vector,
            "residual_rmse": self.residual_rmse,
            "intrinsic_boundary_hit": self.intrinsic_boundary_hit,
            "homography_consistency": self.homography_consistency,
            "pnp_used": self.pnp_used,
            "pnp_point_count": self.pnp_point_count,
            "rvec": self.rvec,
            "tvec": self.tvec,
            "h_world_to_pixel": self.h_world_to_pixel,
            "h_pixel_to_world": self.h_pixel_to_world,
            "quality_issues": self.quality_issues,
            "model_reference": self.model_reference,
        }


class Vehicle3DCalibrationService:
    MIN_BBOX_ONLY_OBSERVATIONS = 3

    def estimate_from_bbox_priors(
        self,
        *,
        frame_width: int,
        frame_height: int,
        intrinsics_prior: CameraIntrinsicsPrior,
        mount_prior: CameraMountPrior,
        vehicle_priors: dict[str, Vehicle3DPrior],
        observations: list[Vehicle3DObservation],
        homography_consistency: HomographyConsistencyInput | None = None,
        weights: VehicleResidualWeights | None = None,
    ) -> Vehicle3DCalibrationResult:
        active_weights = weights or VehicleResidualWeights()
        camera_matrix = self.camera_matrix_from_prior(
            intrinsics_prior,
            frame_width=frame_width,
            frame_height=frame_height,
        )
        fx = float(camera_matrix[0, 0])
        fy = float(camera_matrix[1, 1])
        bounds = self.check_intrinsics_bounds(
            intrinsics_prior,
            fx=fx,
            fy=fy,
            confidence=intrinsics_prior.confidence,
        )
        quality_issues = list(bounds.quality_issues)
        bbox_only = all(not observation.has_explicit_3d_2d_points for observation in observations)
        if bbox_only and len(observations) < self.MIN_BBOX_ONLY_OBSERVATIONS:
            quality_issues.append("bbox_only_observations_below_minimum")
        if bbox_only and observations:
            quality_issues.append("bbox_only_weakly_observable")
        if not observations:
            quality_issues.append("no_vehicle_3d_observations")
        pnp_result = self._solve_explicit_pnp(
            observations,
            camera_matrix=camera_matrix,
            dist_coeffs=np.array(intrinsics_prior.dist_coeffs, dtype=np.float64),
        )
        pnp_used = pnp_result is not None
        pnp_point_count = pnp_result[2] if pnp_result is not None else 0
        h_world_to_pixel: NDArray[np.float64] | None = None
        h_pixel_to_world: NDArray[np.float64] | None = None
        if pnp_result is not None:
            h_world_to_pixel = self.ground_plane_homography_from_pnp(
                camera_matrix=camera_matrix,
                rvec=pnp_result[0],
                tvec=pnp_result[1],
            )
            h_pixel_to_world = np.linalg.inv(h_world_to_pixel).astype(np.float64)

        residual_vector: list[float] = []
        for observation in observations:
            prior = vehicle_priors.get(observation.class_name)
            if prior is None:
                quality_issues.append(f"missing_vehicle_prior:{observation.class_name}")
                continue
            residual_vector.extend(
                self.bbox_envelope_residual(
                    observation=observation,
                    projected_bbox=observation.bbox,
                    vehicle_prior=prior,
                    candidate_length_m=prior.length_m,
                    candidate_width_m=prior.width_m,
                    camera_height_m=mount_prior.height_m,
                    camera_mount_prior=mount_prior,
                    weights=active_weights,
                )
            )

        heading_spread = self._heading_spread_deg(observations)
        if heading_spread is not None and heading_spread > 25.0:
            quality_issues.append("vehicle_lane_direction_inconsistent")

        consistency_dict: dict[str, object] | None = None
        consistency_passed = False
        if homography_consistency is not None:
            consistency = self.evaluate_homography_consistency(homography_consistency)
            consistency_dict = {
                "passed": consistency.passed,
                "quality_issues": consistency.quality_issues,
                "world_to_pixel_rmse_delta_px": homography_consistency.world_to_pixel_rmse_delta_px,
                "grid_corner_mean_shift_px": homography_consistency.grid_corner_mean_shift_px,
                "speed_delta_kmh": homography_consistency.speed_delta_kmh,
            }
            consistency_passed = consistency.passed
            quality_issues.extend(consistency.quality_issues)
        else:
            quality_issues.append("missing_manual_homography_consistency_gate")

        residual_rmse = self._rmse(residual_vector)
        confidence = bounds.confidence
        if bbox_only:
            confidence *= 0.65
        if residual_rmse > 12.0:
            confidence *= 0.5
            quality_issues.append("vehicle_3d_residual_too_high")
        calibration_trusted = (
            not quality_issues
            and consistency_passed
            and confidence >= 0.55
        )
        quality = "excellent" if calibration_trusted else "unstable"
        return Vehicle3DCalibrationResult(
            calibration_source="vehicle_3d_prior_pnp",
            calibration_quality=quality,
            calibration_trusted=calibration_trusted,
            confidence=float(max(0.0, min(1.0, confidence))),
            camera_matrix=camera_matrix.astype(float).tolist(),
            dist_coeffs=list(intrinsics_prior.dist_coeffs),
            residual_vector=[float(value) for value in residual_vector],
            residual_rmse=residual_rmse,
            intrinsic_boundary_hit=bounds.intrinsic_boundary_hit,
            homography_consistency=consistency_dict,
            pnp_used=pnp_used,
            pnp_point_count=pnp_point_count,
            rvec=pnp_result[0].reshape(-1).astype(float).tolist() if pnp_result else None,
            tvec=pnp_result[1].reshape(-1).astype(float).tolist() if pnp_result else None,
            h_world_to_pixel=h_world_to_pixel.astype(float).tolist()
            if h_world_to_pixel is not None
            else None,
            h_pixel_to_world=h_pixel_to_world.astype(float).tolist()
            if h_pixel_to_world is not None
            else None,
            quality_issues=sorted(set(quality_issues)),
        )

    def bbox_envelope_residual(
        self,
        *,
        observation: Vehicle3DObservation,
        projected_bbox: BBox2D,
        vehicle_prior: Vehicle3DPrior,
        candidate_length_m: float,
        candidate_width_m: float,
        camera_height_m: float,
        camera_mount_prior: CameraMountPrior,
        weights: VehicleResidualWeights,
    ) -> list[float]:
        heading = (
            observation.estimated_heading_deg
            if observation.estimated_heading_deg is not None
            else observation.lane_direction_deg
        )
        height_sigma = max(camera_mount_prior.height_sigma_m, 1e-6)
        return [
            observation.bbox.left - projected_bbox.left,
            observation.bbox.right - projected_bbox.right,
            observation.bbox.top - projected_bbox.top,
            observation.bbox.bottom - projected_bbox.bottom,
            weights.lambda_heading * self._angle_diff_deg(heading, observation.lane_direction_deg),
            weights.lambda_length
            * (candidate_length_m - vehicle_prior.length_m)
            / max(vehicle_prior.length_sigma_m, 1e-6),
            weights.lambda_width
            * (candidate_width_m - vehicle_prior.width_m)
            / max(vehicle_prior.width_sigma_m, 1e-6),
            weights.lambda_height
            * (camera_height_m - camera_mount_prior.height_m)
            / height_sigma,
        ]

    def camera_matrix_from_prior(
        self,
        prior: CameraIntrinsicsPrior,
        *,
        frame_width: int,
        frame_height: int,
    ) -> NDArray[np.float64]:
        cx = prior.cx if prior.cx is not None else frame_width / 2.0
        cy = prior.cy if prior.cy is not None else frame_height / 2.0
        fx = prior.fx
        fy = prior.fy
        if fx is None or fy is None:
            if prior.fov_deg is None or prior.fov_deg <= 0:
                focal = float(max(frame_width, frame_height))
            else:
                focal = frame_width / (2.0 * math.tan(math.radians(prior.fov_deg) / 2.0))
            fx = fx if fx is not None else focal
            fy = fy if fy is not None else focal
        return np.array(
            [
                [float(fx), 0.0, float(cx)],
                [0.0, float(fy), float(cy)],
                [0.0, 0.0, 1.0],
            ],
            dtype=np.float64,
        )

    def check_intrinsics_bounds(
        self,
        prior: CameraIntrinsicsPrior,
        *,
        fx: float,
        fy: float,
        confidence: float,
    ) -> IntrinsicsBoundsCheck:
        issues: list[str] = []
        boundary_hit = False
        checked_confidence = confidence
        if prior.fx is not None:
            lower = prior.fx * prior.fx_bounds_scale[0]
            upper = prior.fx * prior.fx_bounds_scale[1]
            if fx < lower or fx > upper:
                issues.append("fx_out_of_bounds")
                checked_confidence = 0.0
            if abs(fx - prior.fx) > prior.fx * 0.8:
                issues.append("focal_length_far_from_prior")
                boundary_hit = True
                checked_confidence *= 0.5
        if prior.fy is not None:
            lower = prior.fy * prior.fx_bounds_scale[0]
            upper = prior.fy * prior.fx_bounds_scale[1]
            if fy < lower or fy > upper:
                issues.append("fy_out_of_bounds")
                checked_confidence = 0.0
            if abs(fy - prior.fy) > prior.fy * 0.8:
                issues.append("focal_length_far_from_prior")
                boundary_hit = True
                checked_confidence *= 0.5
        return IntrinsicsBoundsCheck(
            confidence=float(max(0.0, min(1.0, checked_confidence))),
            intrinsic_boundary_hit=boundary_hit,
            quality_issues=sorted(set(issues)),
        )

    def evaluate_homography_consistency(
        self,
        value: HomographyConsistencyInput,
    ) -> HomographyConsistencyResult:
        issues: list[str] = []
        if (
            value.world_to_pixel_rmse_delta_px is None
            or value.world_to_pixel_rmse_delta_px >= 2.0
        ):
            issues.append("world_to_pixel_rmse_delta_over_2_px")
        if (
            value.grid_corner_mean_shift_px is None
            or value.grid_corner_mean_shift_px >= 5.0
        ):
            issues.append("grid_corner_shift_over_5_px")
        if value.speed_delta_kmh is None or value.speed_delta_kmh >= 3.0:
            issues.append("speed_delta_over_3_kmh")
        return HomographyConsistencyResult(passed=not issues, quality_issues=issues)

    @staticmethod
    def ground_plane_homography_from_pnp(
        *,
        camera_matrix: NDArray[np.float64],
        rvec: NDArray[np.float64],
        tvec: NDArray[np.float64],
    ) -> NDArray[np.float64]:
        try:
            import cv2  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError("OpenCV is required for PnP homography derivation") from exc
        rotation, _ = cv2.Rodrigues(rvec.reshape(3, 1))
        extrinsic_ground_plane = np.column_stack(
            [
                rotation[:, 0],
                rotation[:, 1],
                tvec.reshape(3),
            ],
        )
        homography = camera_matrix @ extrinsic_ground_plane
        scale = homography[2, 2]
        if abs(scale) < 1e-9:
            return homography.astype(np.float64)
        return (homography / scale).astype(np.float64)

    @staticmethod
    def _solve_explicit_pnp(
        observations: list[Vehicle3DObservation],
        *,
        camera_matrix: NDArray[np.float64],
        dist_coeffs: NDArray[np.float64],
    ) -> tuple[NDArray[np.float64], NDArray[np.float64], int] | None:
        object_points: list[list[float]] = []
        image_points: list[list[float]] = []
        for observation in observations:
            for point in observation.optional_keypoints:
                raw_object = point.get("object_point")
                raw_image = point.get("image_point")
                if (
                    isinstance(raw_object, list)
                    and isinstance(raw_image, list)
                    and len(raw_object) == 3
                    and len(raw_image) == 2
                ):
                    object_points.append([float(value) for value in raw_object])
                    image_points.append([float(value) for value in raw_image])
        if len(object_points) < 4:
            return None
        try:
            import cv2  # type: ignore[import-not-found]
        except ImportError:
            return None
        object_array = np.array(object_points, dtype=np.float64)
        image_array = np.array(image_points, dtype=np.float64)
        success, rvec, tvec, _inliers = cv2.solvePnPRansac(
            object_array,
            image_array,
            camera_matrix,
            dist_coeffs.reshape(-1, 1),
            flags=cv2.SOLVEPNP_ITERATIVE,
        )
        if not success:
            return None
        if hasattr(cv2, "solvePnPRefineLM"):
            rvec, tvec = cv2.solvePnPRefineLM(
                object_array,
                image_array,
                camera_matrix,
                dist_coeffs.reshape(-1, 1),
                rvec,
                tvec,
            )
        return rvec.astype(np.float64), tvec.astype(np.float64), len(object_points)

    @staticmethod
    def _rmse(values: list[float]) -> float:
        if not values:
            return 0.0
        return float((sum(value * value for value in values) / len(values)) ** 0.5)

    @staticmethod
    def _angle_diff_deg(a: float, b: float) -> float:
        return float((a - b + 180.0) % 360.0 - 180.0)

    @staticmethod
    def _heading_spread_deg(observations: list[Vehicle3DObservation]) -> float | None:
        if len(observations) < 2:
            return None
        headings = [observation.lane_direction_deg for observation in observations]
        mean = sum(headings) / len(headings)
        return max(
            abs(Vehicle3DCalibrationService._angle_diff_deg(value, mean))
            for value in headings
        )
