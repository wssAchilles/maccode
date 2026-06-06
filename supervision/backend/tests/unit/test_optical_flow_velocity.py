from __future__ import annotations

import numpy as np
import pytest
from domain.speed.view_transformer import ViewTransformer
from infrastructure.cv.optical_flow import OpticalFlowVelocityEstimator


def test_optical_flow_velocity_estimates_bev_world_velocity() -> None:
    cv2 = pytest.importorskip("cv2")
    previous = np.zeros((96, 128), dtype=np.uint8)
    for y in range(48, 78, 8):
        for x in range(44, 76, 8):
            cv2.circle(previous, (x, y), 2, 255, -1)
    transform = np.array([[1, 0, 6], [0, 1, 0]], dtype=np.float32)
    current = cv2.warpAffine(previous, transform, (128, 96))
    estimator = OpticalFlowVelocityEstimator(ViewTransformer(np.eye(3)))

    observation = estimator.estimate(
        previous_frame=previous,
        current_frame=current,
        previous_xyxy=[40.0, 40.0, 80.0, 82.0],
        previous_contact_point=(60.0, 82.0),
        delta_t_sec=0.5,
    )

    assert observation is not None
    assert observation.velocity_mps[0] == pytest.approx(12.0, abs=1.0)
    assert observation.velocity_mps[1] == pytest.approx(0.0, abs=0.5)
    assert observation.confidence >= 0.5


def test_optical_flow_refines_contact_point_with_forward_backward_checked_flow() -> None:
    cv2 = pytest.importorskip("cv2")
    previous = np.zeros((96, 128), dtype=np.uint8)
    for y in range(48, 78, 8):
        for x in range(44, 76, 8):
            cv2.circle(previous, (x, y), 2, 255, -1)
    current = cv2.warpAffine(
        previous,
        np.array([[1, 0, 4], [0, 1, 0]], dtype=np.float32),
        (128, 96),
    )
    estimator = OpticalFlowVelocityEstimator(ViewTransformer(np.eye(3)))

    refined = estimator.refine_contact_point(
        previous_frame=previous,
        current_frame=current,
        previous_xyxy=[40.0, 40.0, 80.0, 82.0],
        previous_contact_point=(60.0, 82.0),
    )

    assert refined is not None
    assert refined.pixel[0] == pytest.approx(64.0, abs=1.0)
    assert refined.measurement_source == "flow_refined_ground_contact"
