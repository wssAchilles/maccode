from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import numpy as np
from domain.calibration.models import CalibrationPoint
from domain.calibration.service import CalibrationService
from domain.detection.models import Detection, Detections
from domain.speed.models import SpeedRecord
from domain.tracking.models import Track
from domain.zones.models import ZoneConfig, ZoneStats
from infrastructure.cv.video_processor import SupervisionVideoProcessor, VideoFrame


class FakeDetector:
    def detect(self, _frame: object, frame_index: int, timestamp_sec: float) -> Detections:
        x1 = 10.0 + frame_index * 3.0
        return Detections(
            items=[Detection([x1, 0.0, x1 + 20.0, 10.0], 0.9, 2, "car")],
            frame_index=frame_index,
            timestamp_sec=timestamp_sec,
        )


class FakeAdapter:
    def track_and_count(
        self,
        detections: Detections,
        line_start: tuple[float, float],
        line_end: tuple[float, float],
        zone_name: str = "main_gate",
    ) -> object:
        detection = detections.items[0]
        return type(
            "AdapterResult",
            (),
            {
                "tracks": [detection.to_track(1, detections.frame_index)],
                "zone_stats": ZoneStats(zone_name, in_count=1, out_count=0),
            },
        )()


class MultiObjectAdapter:
    def track_and_count(
        self,
        detections: Detections,
        line_start: tuple[float, float],
        line_end: tuple[float, float],
        zone_name: str = "main_gate",
    ) -> object:
        tracks = [
            detection.to_track(
                90 if detection.class_id == 9 else index + 1,
                detections.frame_index,
            )
            for index, detection in enumerate(detections.items)
        ]
        return type(
            "AdapterResult",
            (),
            {
                "tracks": tracks,
                "zone_stats": ZoneStats(zone_name, in_count=1, out_count=0),
            },
        )()


class ZeroCountAdapter:
    def track_and_count(
        self,
        detections: Detections,
        line_start: tuple[float, float],
        line_end: tuple[float, float],
        zone_name: str = "main_gate",
    ) -> object:
        tracks = [
            detection.to_track(1, detections.frame_index)
            for detection in detections.items
        ]
        return type(
            "AdapterResult",
            (),
            {
                "tracks": tracks,
                "zone_stats": ZoneStats(zone_name, in_count=0, out_count=0),
            },
        )()


class SequenceDetector:
    def __init__(self, frames: dict[int, list[Detection]]) -> None:
        self.frames = frames

    def detect(self, _frame: object, frame_index: int, timestamp_sec: float) -> Detections:
        return Detections(
            items=self.frames.get(frame_index, []),
            frame_index=frame_index,
            timestamp_sec=timestamp_sec,
        )


def test_supervision_video_processor_generates_math_enriched_frame_report() -> None:
    calibration = CalibrationService().compute_homography(
        [
            CalibrationPoint(0, 0, 0, 0),
            CalibrationPoint(100, 0, 10, 0),
            CalibrationPoint(100, 100, 10, 10),
            CalibrationPoint(0, 100, 0, 10),
        ]
    )
    frames = [
            VideoFrame(
                np.zeros((8, 8, 3), dtype=np.uint8),
                frame_index=frame_index,
                timestamp_sec=(frame_index - 1) / 24.0,
            )
            for frame_index in range(1, 25)
        ]

    report = SupervisionVideoProcessor(
        detector=FakeDetector(),
        adapter=FakeAdapter(),
        calibration=calibration,
        zone=ZoneConfig("main_gate", [0, 5], [100, 5]),
        fps=24.0,
        calibration_context={
            "calibration_source": "video_manual_preset",
            "calibration_trusted": True,
        },
    ).process_frames(frames)

    assert report["active_tracks"][0]["speed_kmh"] is not None
    assert report["active_tracks"][0]["speed_confidence"] is not None
    assert report["active_tracks"][0]["speed_confidence_interval_kmh"] is not None
    assert report["active_tracks"][0]["ground_x_m"] is not None
    assert report["active_tracks"][0]["ground_y_m"] is not None
    assert report["active_tracks"][0]["velocity_x_mps"] is not None
    assert report["active_tracks"][0]["velocity_y_mps"] is not None
    assert report["active_tracks"][0]["heading_deg"] is not None
    assert report["active_tracks"][0]["scale_confidence_label"] == "stable"
    assert (
        report["active_tracks"][0]["calibration_speed_posterior"]["model_reference"]
        == "homography_monte_carlo_speed_posterior"
    )
    assert (
        report["active_tracks"][0]["joint_speed_posterior"]["model_reference"]
        == "joint_speed_uncertainty_posterior_v1"
    )
    assert (
        report["active_tracks"][0]["joint_physics_posterior"]["model_reference"]
        == "joint_physics_posterior_v4"
    )
    assert "primary_risk_source" in report["active_tracks"][0]["joint_physics_posterior"]
    assert "speed_p05_p50_p95_kmh" in report["active_tracks"][0]["joint_physics_posterior"]
    assert "uncertainty_component_ratios" in report["active_tracks"][0]["joint_physics_posterior"]
    assert "near_far_speed_drift_metrics" in report["active_tracks"][0]["joint_physics_posterior"]
    assert report["active_tracks"][0]["body_ground_projection"] is not None
    assert report["active_tracks"][0]["support_contact_anchor"] is not None
    assert report["active_tracks"][0]["contact_phase_probabilities"] is not None
    assert report["active_tracks"][0]["foot_skate_risk"] is not None
    assert report["active_tracks"][0]["near_far_speed_drift_metrics"] is not None
    assert "speed_body_kmh" in report["active_tracks"][0]
    assert "speed_periodic_kmh" in report["active_tracks"][0]
    assert "support_zero_velocity_residual_mps" in report["active_tracks"][0]
    assert "near_far_speed_drift_score" in report["active_tracks"][0]
    assert "geometry_status" in report["active_tracks"][0]
    assert report["active_tracks"][0]["joint_physics_posterior"]["geometry_status"] in {
        "accepted",
        "weak_scale",
        "periodic_inconsistent",
        "foot_skate_invalid",
        None,
    }
    assert report["active_tracks"][0]["contact_state"] == "unknown"
    assert report["active_tracks"][0]["measurement_policy"] is not None
    assert (
        report["speed_nis_diagnostics"]["model_reference"]
        == "nis_consistency_diagnostics_v1"
    )
    assert report["speed_nis_diagnostics"]["sample_count"] > 0
    assert (
        report["speed_geometry_diagnostics"]["model_reference"]
        == "pedestrian_perspective_geometry_guard_v1"
    )
    assert "pedestrian_scale_drift_count" in report["speed_geometry_diagnostics"]
    assert "pedestrian_speed_suppressed_count" in report["speed_geometry_diagnostics"]
    assert "pose_geometry_used_count" in report["speed_geometry_diagnostics"]
    assert "bbox_height_consistency_fail_count" in report["speed_geometry_diagnostics"]
    assert "pedestrian_scale_drift_detected" in report["active_tracks"][0]
    assert "speed_inverse_height_correlation" in report["active_tracks"][0]
    assert "height_consistency_score" in report["active_tracks"][0]
    assert "recommended_speed_scale_factor" in report["active_tracks"][0]
    assert "pedestrian_geometry_model_reference" in report["active_tracks"][0]
    assert "contact_innovation_score" in report["active_tracks"][0]
    assert report["calibration_quality"] == "excellent"
    assert (
        report["calibration_diagnostics"]["pedestrian_geometry_self_supervision"][
            "model_reference"
        ]
        == "pedestrian_head_foot_scale_drift_v1"
    )
    assert report["homography_grid"]["generated_from"] == "inverse_homography_projection"
    assert report["homography_grid"]["calibration_trusted"] is True
    assert report["homography_grid"]["lines"]
    assert report["traffic_flow"]["density_k_veh_per_km"] > 0
    assert report["regional_people_count"]["people_count"] == 0
    assert report["regional_people_count"]["estimation_method"] == "direct_detection_count"
    assert report["infrastructure_semantics"]["dynamic_vehicle_count"] == 1
    assert report["infrastructure_semantics"]["traffic_light_state"] == "unknown"
    assert report["safety_metrics"]["risk_level"] == "nominal"


def test_camera_profile_rules_are_bound_to_runtime_report() -> None:
    calibration = CalibrationService().compute_homography(
        [
            CalibrationPoint(0, 0, 0, 0),
            CalibrationPoint(100, 0, 10, 0),
            CalibrationPoint(100, 100, 10, 10),
            CalibrationPoint(0, 100, 0, 10),
        ]
    )
    frames = [
        VideoFrame(np.zeros((8, 8, 3), dtype=np.uint8), frame_index=1, timestamp_sec=0.0),
        VideoFrame(np.zeros((8, 8, 3), dtype=np.uint8), frame_index=2, timestamp_sec=1.0),
        VideoFrame(np.zeros((8, 8, 3), dtype=np.uint8), frame_index=3, timestamp_sec=2.0),
    ]

    report = SupervisionVideoProcessor(
        detector=FakeDetector(),
        adapter=FakeAdapter(),
        calibration=calibration,
        zone=ZoneConfig("profile_stop_line", [0, 5], [100, 5]),
        fps=24.0,
        calibration_context={
            "camera_profile_id": "test_fixed_camera",
            "profile_tuning": {"speed_limit_kmh": 5.0},
            "profile_polygon_zones": [
                {"name": "pedestrian_density_area", "points_ratio": []},
            ],
            "profile_risk_areas": [{"name": "crosswalk_stop_line", "kind": "stop_line"}],
            "profile_traffic_light_rois": [{"name": "right_signal", "xyxy_ratio": []}],
        },
    ).process_frames(frames)

    assert report["calibration_diagnostics"]["profile_polygon_zones"]
    assert report["calibration_diagnostics"]["profile_risk_areas"]
    assert report["regional_people_count"]["region_name"] == "pedestrian_density_area"
    assert report["infrastructure_semantics"]["configured_traffic_light_rois"] == [
        {"name": "right_signal", "xyxy_ratio": []},
    ]
    assert report["safety_metrics"]["speed_limit_kmh"] == 5.0
    assert report["safety_metrics"]["rule_source"] == "camera_profile_rules"
    assert report["safety_metrics"]["configured_risk_areas"] == [
        {"name": "crosswalk_stop_line", "kind": "stop_line"},
    ]


def test_supervision_video_processor_renders_processed_mp4(tmp_path: Path) -> None:
    calibration = CalibrationService().compute_homography(
        [
            CalibrationPoint(0, 0, 0, 0),
            CalibrationPoint(100, 0, 10, 0),
            CalibrationPoint(100, 100, 10, 10),
            CalibrationPoint(0, 100, 0, 10),
        ]
    )
    output_path = tmp_path / "processed.mp4"
    frames = [
        VideoFrame(np.zeros((100, 100, 3), dtype=np.uint8), frame_index=1, timestamp_sec=0.0),
        VideoFrame(np.zeros((100, 100, 3), dtype=np.uint8), frame_index=2, timestamp_sec=1.0),
        VideoFrame(np.zeros((100, 100, 3), dtype=np.uint8), frame_index=3, timestamp_sec=2.0),
    ]

    SupervisionVideoProcessor(
        detector=FakeDetector(),
        adapter=FakeAdapter(),
        calibration=calibration,
        zone=ZoneConfig("main_gate", [0, 5], [100, 5]),
        fps=12.0,
        frame_width=100,
        frame_height=100,
        rendered_video_path=output_path,
        calibration_context={
            "calibration_source": "video_manual_preset",
            "calibration_trusted": True,
        },
    ).process_frames(frames)

    assert output_path.exists()
    assert output_path.stat().st_size > 0


def test_scene_profile_preset_does_not_generate_homography_grid() -> None:
    calibration = CalibrationService().compute_homography(
        [
            CalibrationPoint(0, 0, 0, 0),
            CalibrationPoint(100, 0, 10, 0),
            CalibrationPoint(100, 100, 10, 10),
            CalibrationPoint(0, 100, 0, 10),
        ]
    )

    report = SupervisionVideoProcessor(
        detector=FakeDetector(),
        adapter=FakeAdapter(),
        calibration=calibration,
        zone=ZoneConfig("analysis_line", [0, 5], [100, 5]),
        fps=24.0,
        calibration_context={
            "calibration_source": "scene_profile_preset",
            "calibration_trusted": False,
        },
    ).process_frames(
        [VideoFrame(np.zeros((100, 100, 3), dtype=np.uint8), frame_index=1, timestamp_sec=0.0)]
    )

    assert report["homography_grid"] is None
    assert report["calibration_diagnostics"]["calibration_trusted"] is False
    assert report["calibration_diagnostics"]["metric_speed_admitted"] is False
    assert (
        report["calibration_diagnostics"]["metric_speed_gate_reason"]
        == "metric_calibration_not_trusted"
    )
    assert report["calibration_diagnostics"]["weak_scale_mode"] is True
    assert report["active_tracks"][0]["speed_kmh"] is None
    assert report["active_tracks"][0]["physics_valid"] is False
    assert report["active_tracks"][0]["quality_label"] == "weak_scale"
    assert report["active_tracks"][0]["scale_confidence_label"] == "weak_scale"
    assert report["active_tracks"][0]["calibration_speed_posterior"] is None
    assert report["active_tracks"][0]["joint_speed_posterior"] is None
    assert report["active_tracks"][0]["weak_calibration_reason"] is not None
    assert (
        "untrusted_calibration_grid_suppressed"
        in report["calibration_diagnostics"]["error_sources"]
    )


def test_metric_speed_gate_rejects_missing_independent_validation() -> None:
    calibration = CalibrationService().compute_homography(
        [
            CalibrationPoint(0, 0, 0, 0),
            CalibrationPoint(100, 0, 10, 0),
            CalibrationPoint(100, 100, 10, 10),
            CalibrationPoint(0, 100, 0, 10),
        ]
    )

    report = SupervisionVideoProcessor(
        detector=FakeDetector(),
        adapter=FakeAdapter(),
        calibration=calibration,
        zone=ZoneConfig("analysis_line", [0, 5], [100, 5]),
        fps=24.0,
        calibration_context={
            "calibration_source": "video_manual_preset",
            "calibration_trusted": True,
            "manual_control_point_count": 6,
            "independent_validation_segment_count": 0,
        },
    ).process_frames(
        [VideoFrame(np.zeros((100, 100, 3), dtype=np.uint8), frame_index=1, timestamp_sec=0.0)]
    )

    assert report["calibration_diagnostics"]["calibration_trusted"] is True
    assert report["calibration_diagnostics"]["metric_speed_admitted"] is False
    assert (
        report["calibration_diagnostics"]["metric_speed_gate_reason"]
        == "missing_independent_metric_validation_segment"
    )
    assert report["active_tracks"][0]["speed_kmh"] is None
    assert report["active_tracks"][0]["physics_valid"] is False
    assert report["active_tracks"][0]["quality_label"] == "weak_scale"


def test_metric_plane_selection_is_propagated_to_track_report() -> None:
    calibration = CalibrationService().compute_homography(
        [
            CalibrationPoint(0, 0, 0, 0),
            CalibrationPoint(100, 0, 10, 0),
            CalibrationPoint(100, 100, 10, 10),
            CalibrationPoint(0, 100, 0, 10),
        ]
    )
    detector = SequenceDetector(
        {
            1: [Detection([60.0, 10.0, 72.0, 42.0], 0.9, 0, "person")],
            2: [Detection([62.0, 10.0, 74.0, 42.0], 0.9, 0, "person")],
        }
    )

    report = SupervisionVideoProcessor(
        detector=detector,
        adapter=FakeAdapter(),
        calibration=calibration,
        zone=ZoneConfig("analysis_line", [0, 50], [100, 50]),
        fps=24.0,
        frame_width=100,
        frame_height=100,
        calibration_context={
            "calibration_source": "video_manual_preset",
            "calibration_trusted": False,
            "metric_planes": [
                {
                    "plane_id": "sidewalk",
                    "plane_kind": "sidewalk",
                    "trusted": True,
                    "pixel_polygon": [[50, 0], [100, 0], [100, 100], [50, 100]],
                    "world_polygon": [[0, 0], [5, 0], [5, 10], [0, 10]],
                    "control_points": [
                        {"pixel_x": 50, "pixel_y": 0, "world_x": 0, "world_y": 0},
                        {"pixel_x": 100, "pixel_y": 0, "world_x": 5, "world_y": 0},
                        {"pixel_x": 100, "pixel_y": 100, "world_x": 5, "world_y": 10},
                        {"pixel_x": 50, "pixel_y": 100, "world_x": 0, "world_y": 10},
                    ],
                }
            ],
        },
    ).process_frames(
        [
            VideoFrame(np.zeros((100, 100, 3), dtype=np.uint8), 1, 0.0),
            VideoFrame(np.zeros((100, 100, 3), dtype=np.uint8), 2, 1.0),
        ]
    )

    track = report["active_tracks"][0]

    assert report["calibration_diagnostics"]["metric_speed_admitted"] is True
    assert report["calibration_diagnostics"]["metric_planes"][0]["plane_id"] == "sidewalk"
    assert track["plane_id"] == "sidewalk"
    assert track["contact_source"] is not None
    assert track["world_position_covariance"] is not None
    assert track["speed_geometry_diagnostics"]["plane_status"] == "selected"


def test_pedestrian_default_road_plane_does_not_output_metric_speed() -> None:
    calibration = CalibrationService().compute_homography(
        [
            CalibrationPoint(0, 0, 0, 0),
            CalibrationPoint(100, 0, 10, 0),
            CalibrationPoint(100, 100, 10, 10),
            CalibrationPoint(0, 100, 0, 10),
        ]
    )
    detector = SequenceDetector(
        {1: [Detection([20.0, 10.0, 32.0, 52.0], 0.9, 0, "person")]}
    )

    report = SupervisionVideoProcessor(
        detector=detector,
        adapter=FakeAdapter(),
        calibration=calibration,
        zone=ZoneConfig("analysis_line", [0, 50], [100, 50]),
        fps=24.0,
        frame_width=100,
        frame_height=100,
        calibration_context={
            "calibration_source": "video_manual_preset",
            "calibration_trusted": True,
        },
    ).process_frames([VideoFrame(np.zeros((100, 100, 3), dtype=np.uint8), 1, 0.0)])

    track = report["active_tracks"][0]

    assert track["speed_kmh"] is None
    assert track["physics_valid"] is False
    assert track["rejection_reason"] == "person_metric_plane_required"
    assert track["speed_geometry_diagnostics"]["pedestrian_metric_admitted"] is False
    assert (
        track["speed_geometry_diagnostics"]["pedestrian_metric_rejection_reason"]
        == "person_metric_plane_required"
    )


def test_pedestrian_bbox_contact_contamination_blocks_sidewalk_speed() -> None:
    calibration = CalibrationService().compute_homography(
        [
            CalibrationPoint(0, 0, 0, 0),
            CalibrationPoint(100, 0, 10, 0),
            CalibrationPoint(100, 100, 10, 10),
            CalibrationPoint(0, 100, 0, 10),
        ]
    )
    detector = SequenceDetector(
        {1: [Detection([55.0, 20.0, 95.0, 55.0], 0.9, 0, "person")]}
    )

    report = SupervisionVideoProcessor(
        detector=detector,
        adapter=FakeAdapter(),
        calibration=calibration,
        zone=ZoneConfig("analysis_line", [0, 50], [100, 50]),
        fps=24.0,
        frame_width=100,
        frame_height=100,
        calibration_context={
            "calibration_source": "video_manual_preset",
            "calibration_trusted": False,
            "metric_planes": [
                {
                    "plane_id": "sidewalk_main",
                    "plane_kind": "sidewalk",
                    "trusted": True,
                    "pixel_polygon": [[50, 0], [100, 0], [100, 100], [50, 100]],
                    "world_polygon": [[0, 0], [5, 0], [5, 10], [0, 10]],
                    "control_points": [
                        {"pixel_x": 50, "pixel_y": 0, "world_x": 0, "world_y": 0},
                        {"pixel_x": 100, "pixel_y": 0, "world_x": 5, "world_y": 0},
                        {"pixel_x": 100, "pixel_y": 100, "world_x": 5, "world_y": 10},
                        {"pixel_x": 50, "pixel_y": 100, "world_x": 0, "world_y": 10},
                    ],
                }
            ],
        },
    ).process_frames([VideoFrame(np.zeros((100, 100, 3), dtype=np.uint8), 1, 0.0)])

    track = report["active_tracks"][0]

    assert track["speed_kmh"] is None
    assert track["physics_valid"] is False
    assert track["rejection_reason"] == "pedestrian_contact_contaminated"
    assert track["speed_geometry_diagnostics"]["bbox_contact_contaminated"] is True


def test_real_video_processor_counts_line_crossing_from_persistent_track_geometry() -> None:
    calibration = CalibrationService().compute_homography(
        [
            CalibrationPoint(0, 0, 0, 0),
            CalibrationPoint(100, 0, 10, 0),
            CalibrationPoint(100, 100, 10, 10),
            CalibrationPoint(0, 100, 0, 10),
        ]
    )
    frames = [
        VideoFrame(np.zeros((100, 100, 3), dtype=np.uint8), frame_index=1, timestamp_sec=0.0),
        VideoFrame(np.zeros((100, 100, 3), dtype=np.uint8), frame_index=2, timestamp_sec=0.1),
    ]
    detector = SequenceDetector(
        {
            1: [Detection([10, 0, 30, 8], 0.9, 2, "car")],
            2: [Detection([10, 12, 30, 24], 0.9, 2, "car")],
        }
    )

    report = SupervisionVideoProcessor(
        detector=detector,
        adapter=ZeroCountAdapter(),
        calibration=calibration,
        zone=ZoneConfig("stop_line", [0, 10], [60, 10]),
        fps=10.0,
        frame_width=100,
        frame_height=100,
        calibration_context={
            "calibration_source": "video_manual_preset",
            "calibration_trusted": True,
        },
    ).process_frames(frames)

    assert report["zone_stats"] == [{"name": "stop_line", "in_count": 1, "out_count": 0}]
    assert report["total_in"] == 1
    assert report["total_out"] == 0


def test_validation_error_suppresses_manual_homography_grid() -> None:
    calibration = CalibrationService().compute_homography(
        [
            CalibrationPoint(0, 0, 0, 0),
            CalibrationPoint(100, 0, 10, 0),
            CalibrationPoint(100, 100, 10, 10),
            CalibrationPoint(0, 100, 0, 10),
        ]
    )

    report = SupervisionVideoProcessor(
        detector=FakeDetector(),
        adapter=FakeAdapter(),
        calibration=calibration,
        zone=ZoneConfig("analysis_line", [0, 5], [100, 5]),
        fps=24.0,
        calibration_context={
            "calibration_source": "video_manual_preset",
            "calibration_trusted": True,
            "validation_max_error_px": 31.0,
        },
    ).process_frames(
        [VideoFrame(np.zeros((100, 100, 3), dtype=np.uint8), frame_index=1, timestamp_sec=0.0)]
    )

    assert report["homography_grid"] is None
    assert report["calibration_diagnostics"]["calibration_trusted"] is False
    assert report["calibration_diagnostics"]["validation_max_error_px"] == 31.0


def test_traffic_flow_ignores_stale_speed_records_for_inactive_tracks() -> None:
    calibration = CalibrationService().compute_homography(
        [
            CalibrationPoint(0, 0, 0, 0),
            CalibrationPoint(100, 0, 10, 0),
            CalibrationPoint(100, 100, 10, 10),
            CalibrationPoint(0, 100, 0, 10),
        ]
    )
    processor = SupervisionVideoProcessor(
        detector=FakeDetector(),
        adapter=FakeAdapter(),
        calibration=calibration,
        zone=ZoneConfig("main_gate", [0, 5], [100, 5]),
        fps=24.0,
    )

    flow = processor._build_traffic_flow(  # noqa: SLF001
        tracks=[],
        speed_records={
            99: SpeedRecord(
                tracker_id=99,
                speed_kmh=88.0,
                timestamp_sec=2.0,
                world_x=0.0,
                world_y=0.0,
            ),
        },
        timestamp_sec=2.0,
    )

    assert flow["space_mean_speed_kmh"] is None


def test_regional_people_count_uses_density_field_integral_for_crowds() -> None:
    calibration = CalibrationService().compute_homography(
        [
            CalibrationPoint(0, 0, 0, 0),
            CalibrationPoint(100, 0, 10, 0),
            CalibrationPoint(100, 100, 10, 10),
            CalibrationPoint(0, 100, 0, 10),
        ]
    )
    processor = SupervisionVideoProcessor(
        detector=FakeDetector(),
        adapter=FakeAdapter(),
        calibration=calibration,
        zone=ZoneConfig("hospital_gate", [0, 50], [100, 50]),
        fps=24.0,
        segment_width_m=10.0,
        segment_length_m=20.0,
    )
    crowd_tracks = [
        Track(
            tracker_id=index,
            class_id=0,
            class_name="person",
            confidence=0.8,
            xyxy=[
                float(10 + (index % 10) * 4),
                float(10 + (index // 10) * 5),
                float(12 + (index % 10) * 4),
                float(18 + (index // 10) * 5),
            ],
            first_seen_frame=1,
            last_seen_frame=1,
        )
        for index in range(42)
    ]

    people = processor._build_regional_people_count(crowd_tracks)  # noqa: SLF001
    density_field = cast(dict[str, Any], people["density_field"])

    assert people["estimation_method"] == "density_field_integral"
    assert people["density_integral_triggered"] is True
    assert float(cast(float, people["integrated_people_count"])) >= 42
    assert float(cast(float, people["density_people_per_sqm"])) > 0
    assert float(cast(float, density_field["cell_size_m"])) > 0
    assert "density_integral_fallback" not in str(people)


def test_regional_people_count_uses_profile_density_polygon_area() -> None:
    calibration = CalibrationService().compute_homography(
        [
            CalibrationPoint(0, 0, 0, 0),
            CalibrationPoint(100, 0, 10, 0),
            CalibrationPoint(100, 100, 10, 10),
            CalibrationPoint(0, 100, 0, 10),
        ]
    )
    processor = SupervisionVideoProcessor(
        detector=FakeDetector(),
        adapter=FakeAdapter(),
        calibration=calibration,
        zone=ZoneConfig("main_gate", [0, 50], [100, 50]),
        fps=24.0,
        segment_width_m=10.0,
        segment_length_m=20.0,
        calibration_context={
            "profile_polygon_zones": [
                {
                    "name": "pedestrian_density_area",
                    "points_ratio": [[0.0, 0.0], [0.5, 0.0], [0.5, 1.0], [0.0, 1.0]],
                }
            ]
        },
    )
    people_tracks = [
        Track(
            tracker_id=index,
            class_id=0,
            class_name="person",
            confidence=0.8,
            xyxy=[10.0 + index * 3, 10.0, 12.0 + index * 3, 18.0],
            first_seen_frame=1,
            last_seen_frame=1,
        )
        for index in range(4)
    ]

    people = processor._build_regional_people_count(people_tracks)  # noqa: SLF001
    density_field = cast(dict[str, Any], people["density_field"])

    assert people["region_name"] == "pedestrian_density_area"
    assert people["density_people_per_sqm"] == 0.04
    assert density_field["visible_area_sqm"] == 100.0
    assert density_field["visible_area_source"] == "configured_roi_polygon"


def test_red_light_roi_state_and_stop_line_violation_are_reported() -> None:
    calibration = CalibrationService().compute_homography(
        [
            CalibrationPoint(0, 0, 0, 0),
            CalibrationPoint(100, 0, 10, 0),
            CalibrationPoint(100, 100, 10, 10),
            CalibrationPoint(0, 100, 0, 10),
        ]
    )
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    frame[5:24, 80:95] = [0, 0, 255]
    detector = SequenceDetector(
        {
            1: [
                Detection([10.0, 20.0, 30.0, 44.0], 0.9, 2, "car"),
                Detection([80.0, 5.0, 95.0, 35.0], 0.9, 9, "traffic light"),
            ],
            2: [
                Detection([10.0, 40.0, 30.0, 62.0], 0.9, 2, "car"),
                Detection([80.0, 5.0, 95.0, 35.0], 0.9, 9, "traffic light"),
            ],
        }
    )

    report = SupervisionVideoProcessor(
        detector=detector,
        adapter=MultiObjectAdapter(),
        calibration=calibration,
        zone=ZoneConfig("stop_line", [0, 50], [100, 50]),
        fps=24.0,
    ).process_frames(
        [
            VideoFrame(frame, frame_index=1, timestamp_sec=0.0),
            VideoFrame(frame, frame_index=2, timestamp_sec=1.0),
        ]
    )

    assert report["infrastructure_semantics"]["traffic_light_state"] == "red"
    assert report["infrastructure_semantics"]["violation_on_crosswalk"] is True
    assert report["infrastructure_semantics"]["red_light_violation_candidate_track_ids"] == [1]
    assert report["safety_metrics"]["red_light_violation_track_ids"] == [1]
    assert report["safety_metrics"]["risk_level"] == "critical"
    traffic_light_track = next(
        track for track in report["active_tracks"] if track["class_id"] == 9
    )
    assert traffic_light_track["physics_valid"] is False
    assert traffic_light_track["quality_label"] == "not_applicable"


def test_green_light_roi_state_does_not_emit_red_light_violation() -> None:
    calibration = CalibrationService().compute_homography(
        [
            CalibrationPoint(0, 0, 0, 0),
            CalibrationPoint(100, 0, 10, 0),
            CalibrationPoint(100, 100, 10, 10),
            CalibrationPoint(0, 100, 0, 10),
        ]
    )
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    frame[18:35, 80:95] = [0, 255, 0]
    detector = SequenceDetector(
        {
            1: [
                Detection([10.0, 20.0, 30.0, 44.0], 0.9, 2, "car"),
                Detection([80.0, 5.0, 95.0, 35.0], 0.9, 9, "traffic light"),
            ],
            2: [
                Detection([10.0, 40.0, 30.0, 62.0], 0.9, 2, "car"),
                Detection([80.0, 5.0, 95.0, 35.0], 0.9, 9, "traffic light"),
            ],
        }
    )

    report = SupervisionVideoProcessor(
        detector=detector,
        adapter=MultiObjectAdapter(),
        calibration=calibration,
        zone=ZoneConfig("stop_line", [0, 50], [100, 50]),
        fps=24.0,
    ).process_frames(
        [
            VideoFrame(frame, frame_index=1, timestamp_sec=0.0),
            VideoFrame(frame, frame_index=2, timestamp_sec=1.0),
        ]
    )

    assert report["infrastructure_semantics"]["traffic_light_state"] == "green"
    assert report["infrastructure_semantics"]["violation_on_crosswalk"] is False
    assert report["safety_metrics"]["red_light_violation_track_ids"] == []


def test_signal_state_uses_last_reliable_roi_state_when_current_crop_is_unclear() -> None:
    calibration = CalibrationService().compute_homography(
        [
            CalibrationPoint(0, 0, 0, 0),
            CalibrationPoint(100, 0, 10, 0),
            CalibrationPoint(100, 100, 10, 10),
            CalibrationPoint(0, 100, 0, 10),
        ]
    )
    red_frame = np.zeros((100, 100, 3), dtype=np.uint8)
    red_frame[5:24, 80:95] = [0, 0, 255]
    dark_frame = np.zeros((100, 100, 3), dtype=np.uint8)
    detector = SequenceDetector(
        {
            1: [Detection([80.0, 5.0, 95.0, 35.0], 0.9, 9, "traffic light")],
            2: [Detection([80.0, 5.0, 95.0, 35.0], 0.9, 9, "traffic light")],
        }
    )

    report = SupervisionVideoProcessor(
        detector=detector,
        adapter=MultiObjectAdapter(),
        calibration=calibration,
        zone=ZoneConfig("stop_line", [0, 50], [100, 50]),
        fps=24.0,
    ).process_frames(
        [
            VideoFrame(red_frame, frame_index=1, timestamp_sec=0.0),
            VideoFrame(dark_frame, frame_index=2, timestamp_sec=1.0),
        ]
    )

    assert report["infrastructure_semantics"]["traffic_light_state"] == "red"
    assert report["infrastructure_semantics"]["traffic_light_state_source"] == (
        "last_reliable_roi_color_rule"
    )
