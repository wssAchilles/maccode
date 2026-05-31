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
class BboxEnvelopeLMResult:
    camera_matrix: NDArray[np.float64]
    mount_prior: CameraMountPrior
    depth_scale: float
    initial_rmse: float | None
    final_rmse: float | None
    iterations: int | None
    success: bool
    boundary_hit: bool
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
    lm_used: bool
    lm_success: bool
    lm_initial_rmse: float | None
    lm_final_rmse: float | None
    lm_iterations: int | None
    optimized_camera_matrix: list[list[float]] | None
    optimized_mount_prior: dict[str, float] | None
    optimized_depth_scale: float | None
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
            "lm_used": self.lm_used,
            "lm_success": self.lm_success,
            "lm_initial_rmse": self.lm_initial_rmse,
            "lm_final_rmse": self.lm_final_rmse,
            "lm_iterations": self.lm_iterations,
            "optimized_camera_matrix": self.optimized_camera_matrix,
            "optimized_mount_prior": self.optimized_mount_prior,
            "optimized_depth_scale": self.optimized_depth_scale,
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
        optimized_camera_matrix: NDArray[np.float64] | None = None
        optimized_mount_prior: CameraMountPrior | None = None
        optimized_depth_scale: float | None = None
        lm_result: BboxEnvelopeLMResult | None = None
        fx = float(camera_matrix[0, 0])
        fy = float(camera_matrix[1, 1])
        bounds = self.check_intrinsics_bounds(
            intrinsics_prior,
            fx=fx,
            fy=fy,
            cx=float(camera_matrix[0, 2]),
            cy=float(camera_matrix[1, 2]),
            frame_width=frame_width,
            frame_height=frame_height,
            dist_coeffs=intrinsics_prior.dist_coeffs,
            confidence=intrinsics_prior.confidence,
        )
        quality_issues = list(bounds.quality_issues)
        bbox_only = all(not observation.has_explicit_3d_2d_points for observation in observations)
        if bbox_only and len(observations) < self.MIN_BBOX_ONLY_OBSERVATIONS:
            quality_issues.append("bbox_only_observations_below_minimum")
        if bbox_only and observations:
            quality_issues.append("bbox_only_weakly_observable")
            lm_result = self._optimize_bbox_envelope(
                frame_width=frame_width,
                frame_height=frame_height,
                intrinsics_prior=intrinsics_prior,
                mount_prior=mount_prior,
                vehicle_priors=vehicle_priors,
                observations=observations,
                weights=active_weights,
                initial_camera_matrix=camera_matrix,
            )
            quality_issues.extend(lm_result.quality_issues)
            if lm_result.success:
                optimized_camera_matrix = lm_result.camera_matrix
                optimized_mount_prior = lm_result.mount_prior
                optimized_depth_scale = lm_result.depth_scale
                camera_matrix = lm_result.camera_matrix
                fx = float(camera_matrix[0, 0])
                fy = float(camera_matrix[1, 1])
                bounds = self.check_intrinsics_bounds(
                    intrinsics_prior,
                    fx=fx,
                    fy=fy,
                    cx=float(camera_matrix[0, 2]),
                    cy=float(camera_matrix[1, 2]),
                    frame_width=frame_width,
                    frame_height=frame_height,
                    dist_coeffs=intrinsics_prior.dist_coeffs,
                    confidence=bounds.confidence,
                )
                quality_issues.extend(bounds.quality_issues)
            if lm_result.boundary_hit:
                quality_issues.append("lm_solution_boundary_hit")
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
                    projected_bbox=self.project_cuboid_envelope(
                        frame_width=frame_width,
                        frame_height=frame_height,
                        camera_matrix=camera_matrix,
                        mount_prior=optimized_mount_prior or mount_prior,
                        vehicle_prior=prior,
                        observation=observation,
                        depth_scale=optimized_depth_scale or 1.0,
                    ),
                    vehicle_prior=prior,
                    candidate_length_m=prior.length_m,
                    candidate_width_m=prior.width_m,
                    camera_height_m=(optimized_mount_prior or mount_prior).height_m,
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
            lm_used=(
                lm_result is not None
                and "scipy_missing_lm_disabled" not in lm_result.quality_issues
            ),
            lm_success=lm_result.success if lm_result is not None else False,
            lm_initial_rmse=lm_result.initial_rmse if lm_result is not None else None,
            lm_final_rmse=lm_result.final_rmse if lm_result is not None else None,
            lm_iterations=lm_result.iterations if lm_result is not None else None,
            optimized_camera_matrix=optimized_camera_matrix.astype(float).tolist()
            if optimized_camera_matrix is not None
            else None,
            optimized_mount_prior={
                "height_m": float(optimized_mount_prior.height_m),
                "pitch_deg": float(optimized_mount_prior.pitch_deg or 0.0),
                "roll_deg": float(optimized_mount_prior.roll_deg or 0.0),
                "yaw_deg": float(optimized_mount_prior.yaw_deg or 0.0),
            }
            if optimized_mount_prior is not None
            else None,
            optimized_depth_scale=optimized_depth_scale,
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

    def project_cuboid_envelope(
        self,
        *,
        frame_width: int,
        frame_height: int,
        camera_matrix: NDArray[np.float64],
        mount_prior: CameraMountPrior,
        vehicle_prior: Vehicle3DPrior,
        observation: Vehicle3DObservation,
        depth_scale: float = 1.0,
    ) -> BBox2D:
        """Project a weakly anchored 3D vehicle cuboid and return its pixel envelope."""
        anchor_pixel = (
            (observation.bbox.left + observation.bbox.right) / 2.0,
            observation.bbox.bottom,
        )
        anchor_world = self._backproject_pixel_to_ground(
            anchor_pixel,
            camera_matrix=camera_matrix,
            mount_prior=mount_prior,
        )
        if anchor_world is None:
            return self._invalid_projection_bbox(frame_width, frame_height)

        heading_deg = (
            observation.estimated_heading_deg
            if observation.estimated_heading_deg is not None
            else observation.lane_direction_deg
        )
        heading = math.radians(heading_deg)
        forward = np.array([math.sin(heading), math.cos(heading)], dtype=np.float64)
        lateral = np.array([math.cos(heading), -math.sin(heading)], dtype=np.float64)
        footprint_center = np.array(
            [
                anchor_world[0] * depth_scale,
                anchor_world[1] * depth_scale,
            ],
            dtype=np.float64,
        )
        half_length = vehicle_prior.length_m / 2.0
        half_width = vehicle_prior.width_m / 2.0
        ground_corners: list[tuple[float, float]] = []
        for length_sign in (-1.0, 1.0):
            for width_sign in (-1.0, 1.0):
                point = (
                    footprint_center
                    + forward * half_length * length_sign
                    + lateral * half_width * width_sign
                )
                ground_corners.append((float(point[0]), float(point[1])))
        world_points = np.array(
            [
                [x, y, z]
                for x, y in ground_corners
                for z in (0.0, vehicle_prior.height_m)
            ],
            dtype=np.float64,
        )
        image_points = self._project_world_points(
            world_points,
            camera_matrix=camera_matrix,
            mount_prior=mount_prior,
        )
        if image_points.size == 0:
            return self._invalid_projection_bbox(frame_width, frame_height)
        return BBox2D(
            left=float(np.min(image_points[:, 0])),
            top=float(np.min(image_points[:, 1])),
            right=float(np.max(image_points[:, 0])),
            bottom=float(np.max(image_points[:, 1])),
        )

    def _optimize_bbox_envelope(
        self,
        *,
        frame_width: int,
        frame_height: int,
        intrinsics_prior: CameraIntrinsicsPrior,
        mount_prior: CameraMountPrior,
        vehicle_priors: dict[str, Vehicle3DPrior],
        observations: list[Vehicle3DObservation],
        weights: VehicleResidualWeights,
        initial_camera_matrix: NDArray[np.float64],
    ) -> BboxEnvelopeLMResult:
        try:
            from scipy.optimize import least_squares
        except ImportError:
            return BboxEnvelopeLMResult(
                camera_matrix=initial_camera_matrix,
                mount_prior=mount_prior,
                depth_scale=1.0,
                initial_rmse=None,
                final_rmse=None,
                iterations=None,
                success=False,
                boundary_hit=False,
                quality_issues=["scipy_missing_lm_disabled"],
            )

        usable = [
            observation
            for observation in observations
            if observation.class_name in vehicle_priors
        ]
        if len(usable) < self.MIN_BBOX_ONLY_OBSERVATIONS:
            return BboxEnvelopeLMResult(
                camera_matrix=initial_camera_matrix,
                mount_prior=mount_prior,
                depth_scale=1.0,
                initial_rmse=None,
                final_rmse=None,
                iterations=None,
                success=False,
                boundary_hit=False,
                quality_issues=["bbox_only_observations_below_minimum"],
            )

        prior_fx = intrinsics_prior.fx or float(initial_camera_matrix[0, 0])
        prior_fy = intrinsics_prior.fy or float(initial_camera_matrix[1, 1])
        prior_cx = intrinsics_prior.cx if intrinsics_prior.cx is not None else frame_width / 2.0
        prior_cy = intrinsics_prior.cy if intrinsics_prior.cy is not None else frame_height / 2.0
        height_sigma = max(mount_prior.height_sigma_m, 0.25)
        initial = np.array(
            [
                float(initial_camera_matrix[0, 0]),
                float(initial_camera_matrix[1, 1]),
                float(initial_camera_matrix[0, 2]),
                float(initial_camera_matrix[1, 2]),
                float(mount_prior.height_m),
                float(mount_prior.pitch_deg or 8.0),
                float(mount_prior.yaw_deg or 0.0),
                1.0,
            ],
            dtype=np.float64,
        )
        cx_delta = frame_width * 0.05
        cy_delta = frame_height * 0.05
        lower = np.array(
            [
                prior_fx * intrinsics_prior.fx_bounds_scale[0],
                prior_fy * intrinsics_prior.fx_bounds_scale[0],
                prior_cx - cx_delta,
                prior_cy - cy_delta,
                max(0.5, mount_prior.height_m - 3.0 * height_sigma),
                -45.0,
                -45.0,
                0.5,
            ],
            dtype=np.float64,
        )
        upper = np.array(
            [
                prior_fx * intrinsics_prior.fx_bounds_scale[1],
                prior_fy * intrinsics_prior.fx_bounds_scale[1],
                prior_cx + cx_delta,
                prior_cy + cy_delta,
                mount_prior.height_m + 3.0 * height_sigma,
                45.0,
                45.0,
                2.0,
            ],
            dtype=np.float64,
        )
        initial = np.minimum(np.maximum(initial, lower + 1e-6), upper - 1e-6)

        def unpack(
            params: NDArray[np.float64],
        ) -> tuple[NDArray[np.float64], CameraMountPrior, float]:
            camera_matrix = np.array(
                [
                    [float(params[0]), 0.0, float(params[2])],
                    [0.0, float(params[1]), float(params[3])],
                    [0.0, 0.0, 1.0],
                ],
                dtype=np.float64,
            )
            optimized_mount = CameraMountPrior(
                height_m=float(params[4]),
                pitch_deg=float(params[5]),
                roll_deg=mount_prior.roll_deg,
                yaw_deg=float(params[6]),
                height_sigma_m=mount_prior.height_sigma_m,
                source=mount_prior.source,
            )
            return camera_matrix, optimized_mount, float(params[7])

        def residuals(params: NDArray[np.float64]) -> NDArray[np.float64]:
            candidate_camera_matrix, candidate_mount, candidate_depth_scale = unpack(params)
            values: list[float] = []
            for observation in usable:
                prior = vehicle_priors[observation.class_name]
                projected = self.project_cuboid_envelope(
                    frame_width=frame_width,
                    frame_height=frame_height,
                    camera_matrix=candidate_camera_matrix,
                    mount_prior=candidate_mount,
                    vehicle_prior=prior,
                    observation=observation,
                    depth_scale=candidate_depth_scale,
                )
                values.extend(
                    self.bbox_envelope_residual(
                        observation=observation,
                        projected_bbox=projected,
                        vehicle_prior=prior,
                        candidate_length_m=prior.length_m,
                        candidate_width_m=prior.width_m,
                        camera_height_m=candidate_mount.height_m,
                        camera_mount_prior=mount_prior,
                        weights=weights,
                    )
                )
            return np.array(values, dtype=np.float64)

        initial_residuals = residuals(initial)
        result = least_squares(
            residuals,
            initial,
            bounds=(lower, upper),
            max_nfev=80,
            loss="soft_l1",
            f_scale=10.0,
        )
        camera_matrix, optimized_mount, depth_scale = unpack(result.x.astype(np.float64))
        final_residuals = residuals(result.x.astype(np.float64))
        boundary_hit = bool(
            np.any(result.x <= lower + np.maximum(np.abs(lower), 1.0) * 0.02)
            or np.any(result.x >= upper - np.maximum(np.abs(upper), 1.0) * 0.02)
        )
        issues: list[str] = []
        if boundary_hit:
            issues.append("lm_solution_boundary_hit")
        if not result.success:
            issues.append("lm_optimizer_failed")
        final_rmse = self._rmse([float(value) for value in final_residuals])
        if final_rmse > 12.0:
            issues.append("vehicle_3d_residual_too_high")
        return BboxEnvelopeLMResult(
            camera_matrix=camera_matrix,
            mount_prior=optimized_mount,
            depth_scale=depth_scale,
            initial_rmse=self._rmse([float(value) for value in initial_residuals]),
            final_rmse=final_rmse,
            iterations=int(result.nfev),
            success=bool(result.success),
            boundary_hit=boundary_hit,
            quality_issues=issues,
        )

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
        cx: float | None = None,
        cy: float | None = None,
        frame_width: int | None = None,
        frame_height: int | None = None,
        dist_coeffs: tuple[float, float, float, float, float] | None = None,
        distortion_authorized: bool = False,
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
            if fx <= lower * 1.02 or fx >= upper * 0.98:
                boundary_hit = True
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
            if fy <= lower * 1.02 or fy >= upper * 0.98:
                boundary_hit = True
        if (
            frame_width is not None
            and frame_height is not None
            and cx is not None
            and cy is not None
        ):
            expected_cx = prior.cx if prior.cx is not None else frame_width / 2.0
            expected_cy = prior.cy if prior.cy is not None else frame_height / 2.0
            cx_delta = frame_width * 0.05
            cy_delta = frame_height * 0.05
            if cx < expected_cx - cx_delta or cx > expected_cx + cx_delta:
                issues.append("principal_point_out_of_bounds")
                boundary_hit = True
                checked_confidence = 0.0
            if cy < expected_cy - cy_delta or cy > expected_cy + cy_delta:
                issues.append("principal_point_out_of_bounds")
                boundary_hit = True
                checked_confidence = 0.0
        if dist_coeffs is not None and not distortion_authorized:
            if any(abs(value) > 1e-12 for value in dist_coeffs):
                issues.append("distortion_not_authorized")
                checked_confidence = 0.0
        return IntrinsicsBoundsCheck(
            confidence=float(max(0.0, min(1.0, checked_confidence))),
            intrinsic_boundary_hit=boundary_hit,
            quality_issues=sorted(set(issues)),
        )

    def _backproject_pixel_to_ground(
        self,
        pixel: tuple[float, float],
        *,
        camera_matrix: NDArray[np.float64],
        mount_prior: CameraMountPrior,
    ) -> tuple[float, float] | None:
        fx = float(camera_matrix[0, 0])
        fy = float(camera_matrix[1, 1])
        cx = float(camera_matrix[0, 2])
        cy = float(camera_matrix[1, 2])
        if abs(fx) < 1e-9 or abs(fy) < 1e-9:
            return None
        normalized_x = (pixel[0] - cx) / fx
        normalized_y = (pixel[1] - cy) / fy
        pitch = math.radians(mount_prior.pitch_deg or 0.0)
        sin_pitch = math.sin(pitch)
        cos_pitch = math.cos(pitch)
        denominator = normalized_y * cos_pitch + sin_pitch
        if abs(denominator) < 1e-9:
            return None
        y_world = mount_prior.height_m * (cos_pitch - normalized_y * sin_pitch) / denominator
        z_camera_depth = sin_pitch * mount_prior.height_m + cos_pitch * y_world
        x_world = normalized_x * z_camera_depth
        yaw = math.radians(mount_prior.yaw_deg or 0.0)
        cos_yaw = math.cos(yaw)
        sin_yaw = math.sin(yaw)
        inv_x = cos_yaw * x_world + sin_yaw * y_world
        inv_y = -sin_yaw * x_world + cos_yaw * y_world
        if not math.isfinite(inv_x) or not math.isfinite(inv_y):
            return None
        return (float(inv_x), float(inv_y))

    def _project_world_points(
        self,
        world_points: NDArray[np.float64],
        *,
        camera_matrix: NDArray[np.float64],
        mount_prior: CameraMountPrior,
    ) -> NDArray[np.float64]:
        camera_points = self._world_to_camera_points(world_points, mount_prior=mount_prior)
        depths = camera_points[:, 2]
        valid = depths > 1e-6
        if not np.any(valid):
            return np.empty((0, 2), dtype=np.float64)
        camera_points = camera_points[valid]
        projected = np.column_stack(
            [
                camera_matrix[0, 0] * (camera_points[:, 0] / camera_points[:, 2])
                + camera_matrix[0, 2],
                camera_matrix[1, 1] * (camera_points[:, 1] / camera_points[:, 2])
                + camera_matrix[1, 2],
            ],
        )
        finite_mask = np.isfinite(projected).all(axis=1)
        return projected[finite_mask].astype(np.float64)

    @staticmethod
    def _world_to_camera_points(
        world_points: NDArray[np.float64],
        *,
        mount_prior: CameraMountPrior,
    ) -> NDArray[np.float64]:
        yaw = math.radians(mount_prior.yaw_deg or 0.0)
        pitch = math.radians(mount_prior.pitch_deg or 0.0)
        cos_yaw = math.cos(yaw)
        sin_yaw = math.sin(yaw)
        x_yawed = cos_yaw * world_points[:, 0] - sin_yaw * world_points[:, 1]
        y_yawed = sin_yaw * world_points[:, 0] + cos_yaw * world_points[:, 1]
        y_down = mount_prior.height_m - world_points[:, 2]
        z_forward = y_yawed
        cos_pitch = math.cos(pitch)
        sin_pitch = math.sin(pitch)
        camera_y = cos_pitch * y_down - sin_pitch * z_forward
        camera_z = sin_pitch * y_down + cos_pitch * z_forward
        return np.column_stack([x_yawed, camera_y, camera_z]).astype(np.float64)

    @staticmethod
    def _invalid_projection_bbox(frame_width: int, frame_height: int) -> BBox2D:
        return BBox2D(
            left=-float(frame_width),
            top=-float(frame_height),
            right=float(frame_width) * 2.0,
            bottom=float(frame_height) * 2.0,
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
