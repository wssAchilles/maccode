from __future__ import annotations

import cv2
import numpy as np
import pytest
from domain.calibration.vehicle_3d import (
    BBox2D,
    CameraIntrinsicsPrior,
    CameraMountPrior,
    HomographyConsistencyInput,
    Vehicle3DCalibrationService,
    Vehicle3DObservation,
    Vehicle3DPrior,
    VehicleResidualWeights,
)


def test_single_bbox_only_observation_is_marked_underdetermined() -> None:
    result = Vehicle3DCalibrationService().estimate_from_bbox_priors(
        frame_width=1280,
        frame_height=720,
        intrinsics_prior=CameraIntrinsicsPrior(fov_deg=60.0, confidence=0.8),
        mount_prior=CameraMountPrior(height_m=7.0, height_sigma_m=1.0),
        vehicle_priors={
            "car": Vehicle3DPrior(length_m=4.5, width_m=1.8, height_m=1.5),
        },
        observations=[
            Vehicle3DObservation(
                class_name="car",
                bbox=BBox2D(left=500.0, top=360.0, right=620.0, bottom=480.0),
                frame_index=1,
                lane_direction_deg=12.0,
            ),
        ],
    )

    assert result.calibration_source == "vehicle_3d_prior_pnp"
    assert result.calibration_quality == "unstable"
    assert result.calibration_trusted is False
    assert "bbox_only_observations_below_minimum" in result.quality_issues


def test_bbox_envelope_residual_contains_bbox_heading_size_and_height_terms() -> None:
    service = Vehicle3DCalibrationService()
    residual = service.bbox_envelope_residual(
        observation=Vehicle3DObservation(
            class_name="car",
            bbox=BBox2D(left=10.0, top=20.0, right=110.0, bottom=120.0),
            frame_index=1,
            lane_direction_deg=10.0,
            estimated_heading_deg=15.0,
        ),
        projected_bbox=BBox2D(left=12.0, top=18.0, right=111.0, bottom=122.0),
        vehicle_prior=Vehicle3DPrior(
            length_m=4.5,
            width_m=1.8,
            height_m=1.5,
            length_sigma_m=0.3,
            width_sigma_m=0.2,
            height_sigma_m=0.2,
        ),
        candidate_length_m=4.8,
        candidate_width_m=1.6,
        camera_height_m=7.5,
        camera_mount_prior=CameraMountPrior(height_m=7.0, height_sigma_m=1.0),
        weights=VehicleResidualWeights(),
    )

    assert residual[:4] == pytest.approx([-2.0, -1.0, 2.0, -2.0])
    assert residual[4] == pytest.approx(0.8 * 5.0)
    assert residual[5] == pytest.approx(1.0)
    assert residual[6] == pytest.approx(-1.0)
    assert residual[7] == pytest.approx(0.6)


def test_intrinsics_boundary_penalizes_weak_focal_length_solution() -> None:
    service = Vehicle3DCalibrationService()
    prior = CameraIntrinsicsPrior(fx=1000.0, fy=1000.0, cx=640.0, cy=360.0)

    checked = service.check_intrinsics_bounds(
        prior,
        fx=1900.0,
        fy=1000.0,
        confidence=0.8,
    )

    assert checked.intrinsic_boundary_hit is True
    assert checked.confidence == pytest.approx(0.4)
    assert "focal_length_far_from_prior" in checked.quality_issues


def test_homography_consistency_gate_rejects_speed_delta_over_threshold() -> None:
    service = Vehicle3DCalibrationService()

    consistent = service.evaluate_homography_consistency(
        HomographyConsistencyInput(
            world_to_pixel_rmse_delta_px=1.5,
            grid_corner_mean_shift_px=4.0,
            speed_delta_kmh=2.0,
        )
    )
    inconsistent = service.evaluate_homography_consistency(
        HomographyConsistencyInput(
            world_to_pixel_rmse_delta_px=1.5,
            grid_corner_mean_shift_px=4.0,
            speed_delta_kmh=4.0,
        )
    )

    assert consistent.passed is True
    assert inconsistent.passed is False
    assert "speed_delta_over_3_kmh" in inconsistent.quality_issues


def test_explicit_3d_2d_keypoints_use_solvepnp_path() -> None:
    camera_matrix = np.array(
        [[800.0, 0.0, 640.0], [0.0, 800.0, 360.0], [0.0, 0.0, 1.0]],
        dtype=np.float64,
    )
    object_points = np.array(
        [
            [-1.0, -2.0, 0.0],
            [1.0, -2.0, 0.0],
            [1.0, 2.0, 0.0],
            [-1.0, 2.0, 0.0],
            [-1.0, -2.0, 1.5],
            [1.0, -2.0, 1.5],
            [1.0, 2.0, 1.5],
            [-1.0, 2.0, 1.5],
        ],
        dtype=np.float64,
    )
    image_points, _ = cv2.projectPoints(
        object_points,
        np.array([0.08, -0.12, 0.02], dtype=np.float64),
        np.array([0.0, 0.0, 12.0], dtype=np.float64),
        camera_matrix,
        np.zeros((5, 1), dtype=np.float64),
    )
    flattened = image_points.reshape(-1, 2)
    observation = Vehicle3DObservation(
        class_name="car",
        bbox=BBox2D(
            left=float(flattened[:, 0].min()),
            top=float(flattened[:, 1].min()),
            right=float(flattened[:, 0].max()),
            bottom=float(flattened[:, 1].max()),
        ),
        frame_index=1,
        lane_direction_deg=0.0,
        optional_keypoints=[
            {
                "object_point": object_point.tolist(),
                "image_point": image_point.tolist(),
            }
            for object_point, image_point in zip(object_points, flattened, strict=True)
        ],
    )

    result = Vehicle3DCalibrationService().estimate_from_bbox_priors(
        frame_width=1280,
        frame_height=720,
        intrinsics_prior=CameraIntrinsicsPrior(
            fx=800.0,
            fy=800.0,
            cx=640.0,
            cy=360.0,
        ),
        mount_prior=CameraMountPrior(height_m=7.0, height_sigma_m=1.0),
        vehicle_priors={
            "car": Vehicle3DPrior(length_m=4.5, width_m=1.8, height_m=1.5),
        },
        observations=[observation],
    )

    assert result.pnp_used is True
    assert result.pnp_point_count == 8
    assert result.h_world_to_pixel is not None
    assert result.h_pixel_to_world is not None
    assert "bbox_only_observations_below_minimum" not in result.quality_issues
