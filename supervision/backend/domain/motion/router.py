from __future__ import annotations

from domain.motion.models import MotionProfile


class MotionRouter:
    VEHICLE_CLASS_IDS = {2, 5, 7}
    LOW_INERTIA_CLASS_IDS = {0, 1, 3}
    STATIC_INFRASTRUCTURE_CLASS_IDS = {9, 10, 11}

    def route_class(self, class_id: int) -> MotionProfile:
        if class_id in self.VEHICLE_CLASS_IDS:
            return MotionProfile(
                category="high_inertia_dynamic",
                process_noise="low",
                should_track=True,
                should_estimate_speed=True,
                track_buffer=30,
                matching_threshold=0.8,
                context_role="traffic_actor",
                fallback_models=["homography", "kalman_smoothing"],
            )
        if class_id in self.LOW_INERTIA_CLASS_IDS:
            return MotionProfile(
                category="low_inertia_dynamic",
                process_noise="high",
                should_track=True,
                should_estimate_speed=True,
                track_buffer=15,
                matching_threshold=0.6,
                context_role="vulnerable_actor",
                fallback_models=["homography", "high_q_filter", "density_integral"],
            )
        if class_id in self.STATIC_INFRASTRUCTURE_CLASS_IDS:
            return MotionProfile(
                category="static_infrastructure",
                process_noise="none",
                should_track=False,
                should_estimate_speed=False,
                track_buffer=0,
                matching_threshold=0.0,
                context_role="traffic_context",
                fallback_models=["state_extraction"],
            )
        return MotionProfile(
            category="unknown_dynamic",
            process_noise="medium",
            should_track=True,
            should_estimate_speed=False,
            track_buffer=10,
            matching_threshold=0.5,
            context_role="unknown_actor",
            fallback_models=["manual_review"],
        )
