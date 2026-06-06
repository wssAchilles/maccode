from __future__ import annotations

import pytest
from domain.speed.contact_fusion import ContactPointFusion, ContactPointObservation


def test_pose_high_confidence_pulls_fused_point_toward_ankle() -> None:
    fused = ContactPointFusion().fuse(
        [
            ContactPointObservation(
                pixel=(50.0, 100.0),
                source="bbox_ground_contact",
                confidence=0.6,
                sigma_px=8.0,
            ),
            ContactPointObservation(
                pixel=(54.0, 92.0),
                source="pose_ankle_ground_contact",
                confidence=0.95,
                sigma_px=1.5,
            ),
        ]
    )

    assert fused.pixel[1] == pytest.approx(92.0, abs=1.5)
    assert fused.weights["pose_ankle_ground_contact"] > fused.weights["bbox_ground_contact"]


def test_disabled_flow_observation_does_not_participate() -> None:
    fused = ContactPointFusion().fuse(
        [
            ContactPointObservation(
                pixel=(10.0, 20.0),
                source="bbox_ground_contact",
                confidence=0.7,
                sigma_px=4.0,
            ),
            ContactPointObservation(
                pixel=(100.0, 200.0),
                source="flow_refined_ground_contact",
                confidence=0.9,
                sigma_px=1.0,
                enabled=False,
            ),
        ]
    )

    assert fused.pixel == (10.0, 20.0)
    assert fused.sources == ["bbox_ground_contact"]
