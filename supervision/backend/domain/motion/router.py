from __future__ import annotations

from domain.motion.models import MotionProfile


class MotionRouter:
    VEHICLE_CLASS_IDS = {2, 3, 5, 7}
    HEAVY_VEHICLE_CLASS_IDS = {5, 7}
    LOW_INERTIA_CLASS_IDS = {0, 1}
    STATIC_INFRASTRUCTURE_CLASS_IDS = {9, 10, 11}

    def route_class(self, class_id: int) -> MotionProfile:
        if class_id == 2:
            return MotionProfile(
                category="high_inertia_dynamic",
                process_noise="low",
                should_track=True,
                should_estimate_speed=True,
                track_buffer=30,
                matching_threshold=0.8,
                context_role="traffic_actor",
                fallback_models=["homography", "kalman_smoothing"],
                nominal_speed_kmh=50.0,
                max_speed_kmh=120.0,
                hard_max_speed_kmh=160.0,
                max_acceleration_mps2=7.0,
                min_track_age_frames=5,
                regression_window_sec=0.9,
                confidence_floor=0.45,
            )
        if class_id in self.HEAVY_VEHICLE_CLASS_IDS:
            return MotionProfile(
                category="heavy_vehicle_dynamic",
                process_noise="low",
                should_track=True,
                should_estimate_speed=True,
                track_buffer=30,
                matching_threshold=0.82,
                context_role="traffic_actor",
                fallback_models=["homography", "kalman_smoothing", "heavy_vehicle_prior"],
                nominal_speed_kmh=35.0,
                max_speed_kmh=90.0,
                hard_max_speed_kmh=110.0,
                max_acceleration_mps2=3.5,
                min_track_age_frames=6,
                regression_window_sec=1.2,
                confidence_floor=0.45,
            )
        if class_id == 3:
            return MotionProfile(
                category="motorcycle_dynamic",
                process_noise="medium",
                should_track=True,
                should_estimate_speed=True,
                track_buffer=24,
                matching_threshold=0.75,
                context_role="traffic_actor",
                fallback_models=["homography", "kalman_smoothing", "motorcycle_prior"],
                nominal_speed_kmh=45.0,
                max_speed_kmh=90.0,
                hard_max_speed_kmh=120.0,
                max_acceleration_mps2=8.0,
                min_track_age_frames=5,
                regression_window_sec=0.9,
                confidence_floor=0.42,
            )
        if class_id in self.LOW_INERTIA_CLASS_IDS:
            if class_id == 1:
                return MotionProfile(
                    category="bicycle_dynamic",
                    process_noise="medium",
                    should_track=True,
                    should_estimate_speed=True,
                    track_buffer=18,
                    matching_threshold=0.65,
                    context_role="vulnerable_actor",
                    fallback_models=["homography", "medium_q_filter", "density_integral"],
                    nominal_speed_kmh=18.0,
                    max_speed_kmh=35.0,
                    hard_max_speed_kmh=45.0,
                    max_acceleration_mps2=5.0,
                    min_track_age_frames=6,
                    regression_window_sec=1.0,
                    confidence_floor=0.40,
                )
            return MotionProfile(
                category="low_inertia_dynamic",
                process_noise="high",
                should_track=True,
                should_estimate_speed=True,
                track_buffer=15,
                matching_threshold=0.6,
                context_role="vulnerable_actor",
                fallback_models=["homography", "high_q_filter", "density_integral"],
                nominal_speed_kmh=5.0,
                max_speed_kmh=18.0,
                hard_max_speed_kmh=25.0,
                max_acceleration_mps2=4.0,
                min_track_age_frames=8,
                regression_window_sec=1.2,
                confidence_floor=0.38,
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
                nominal_speed_kmh=0.0,
                max_speed_kmh=0.0,
                hard_max_speed_kmh=0.0,
                max_acceleration_mps2=0.0,
                min_track_age_frames=0,
                regression_window_sec=0.0,
                confidence_floor=1.0,
            )
        return MotionProfile(
            category="unknown_dynamic",
            process_noise="high",
            should_track=True,
            should_estimate_speed=True,
            track_buffer=10,
            matching_threshold=0.5,
            context_role="unknown_actor",
            fallback_models=["manual_review"],
            nominal_speed_kmh=10.0,
            max_speed_kmh=25.0,
            hard_max_speed_kmh=35.0,
            max_acceleration_mps2=4.0,
            min_track_age_frames=10,
            regression_window_sec=1.2,
            confidence_floor=0.95,
        )
