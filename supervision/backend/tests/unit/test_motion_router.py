from __future__ import annotations

from domain.motion.router import MotionRouter


def test_vehicle_class_routes_to_high_inertia_profile() -> None:
    profile = MotionRouter().route_class(2)

    assert profile.category == "high_inertia_dynamic"
    assert profile.process_noise == "low"
    assert profile.should_track is True
    assert profile.should_estimate_speed is True
    assert profile.track_buffer == 30


def test_person_class_routes_to_sensitive_dynamic_profile() -> None:
    profile = MotionRouter().route_class(0)

    assert profile.category == "low_inertia_dynamic"
    assert profile.process_noise == "high"
    assert profile.matching_threshold == 0.6
    assert "density_integral" in profile.fallback_models


def test_static_infrastructure_skips_tracking_and_speed() -> None:
    profile = MotionRouter().route_class(9)

    assert profile.category == "static_infrastructure"
    assert profile.should_track is False
    assert profile.should_estimate_speed is False
    assert profile.context_role == "traffic_context"
