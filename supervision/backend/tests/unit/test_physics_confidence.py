from __future__ import annotations

from domain.speed.physics_confidence import PhysicsConfidenceModel


def test_bbox_contact_is_less_confident_than_pose_contact() -> None:
    model = PhysicsConfidenceModel()

    pose = model.score(
        measurement_confidence=0.9,
        contact_source="pose_ankle_contact",
    )
    bbox = model.score(
        measurement_confidence=0.9,
        contact_source="bbox_ground_contact",
    )

    assert pose.contact_confidence > bbox.contact_confidence
    assert pose.physics_confidence > bbox.physics_confidence


def test_calibration_confidence_degrades_with_rmse_and_validation_error() -> None:
    model = PhysicsConfidenceModel()

    trusted = model.score(
        calibration_rmse_m=0.05,
        validation_error_px=3.0,
        local_scale_factor=1.0,
    )
    weak = model.score(
        calibration_rmse_m=1.8,
        validation_error_px=45.0,
        local_scale_factor=6.0,
    )

    assert trusted.calibration_confidence > weak.calibration_confidence
    assert trusted.physics_confidence > weak.physics_confidence
    assert weak.confidence_rejection_reason == "calibration_confidence"


def test_tracking_confidence_degrades_with_id_switch_risk() -> None:
    model = PhysicsConfidenceModel()

    stable = model.score(id_switch_risk=0.0, tracking_integrity_state="stable")
    risky = model.score(id_switch_risk=0.95, tracking_integrity_state="id_switch")

    assert stable.tracking_confidence > risky.tracking_confidence
    assert stable.physics_confidence > risky.physics_confidence
