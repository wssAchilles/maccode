from __future__ import annotations

import numpy as np
import pytest
from domain.calibration.camera_model import CoordinateSpaceContract
from domain.calibration.models import HomographyResult
from domain.detection.models import Detection, Detections
from domain.detection.service import DetectionService
from domain.reports.generators import ReportGenerator
from domain.speed.contact_state import PedestrianContactStateEstimator
from domain.speed.ground_contact import GroundContactPoint
from domain.speed.models import SpeedRecord
from domain.tracking.integrity import TrackingIntegrityResult
from domain.tracking.models import Track
from domain.tracking.service import TrackingService
from domain.zones.models import ZoneConfig
from domain.zones.service import ZoneService
from infrastructure.cv.video_processor import SupervisionVideoProcessor


def _homography_result(matrix: np.ndarray) -> HomographyResult:
    return HomographyResult(
        homography_matrix=matrix.astype(float),
        reprojection_rmse=0.1,
        pixel_to_world_rmse_m=0.1,
        world_to_pixel_rmse_px=1.0,
        inlier_count=4,
        condition_number=100.0,
        inlier_mask=[True, True, True, True],
        calibration_quality="excellent",
    )


def test_detection_service_converts_injected_predictions() -> None:
    service = DetectionService(
        model_path="synthetic.pt",
        predictor=lambda _frame: [
            {
                "xyxy": [10, 20, 30, 40],
                "confidence": 0.91,
                "class_id": 2,
                "class_name": "car",
            },
            {
                "xyxy": [0, 0, 5, 5],
                "confidence": 0.10,
                "class_id": 9,
                "class_name": "traffic light",
            },
        ],
        confidence_threshold=0.25,
    )

    detections = service.detect(frame=object(), frame_index=7, timestamp_sec=1.4)

    assert len(detections.items) == 1
    assert detections.frame_index == 7
    assert detections.items[0].class_name == "car"


def test_tracking_service_preserves_tracker_id_for_overlapping_detection() -> None:
    tracker = TrackingService(iou_threshold=0.3)
    first = Detections(
        items=[Detection([10, 10, 30, 30], 0.9, 2, "car")],
        frame_index=1,
        timestamp_sec=0.0,
    )
    second = Detections(
        items=[Detection([12, 10, 32, 30], 0.88, 2, "car")],
        frame_index=2,
        timestamp_sec=0.1,
    )

    first_tracks = tracker.update(first)
    second_tracks = tracker.update(second)

    assert first_tracks[0].tracker_id == second_tracks[0].tracker_id
    assert second_tracks[0].last_seen_frame == 2


def test_tracking_service_recovers_low_confidence_detection_without_new_track() -> None:
    tracker = TrackingService(iou_threshold=0.3)
    first = Detections(
        items=[Detection([10, 10, 30, 30], 0.9, 2, "car")],
        frame_index=1,
        timestamp_sec=0.0,
    )
    second = Detections(
        items=[Detection([12, 10, 32, 30], 0.3, 2, "car")],
        frame_index=2,
        timestamp_sec=0.1,
    )

    first_tracks = tracker.update(first)
    second_tracks = tracker.update(second)

    assert len(second_tracks) == 1
    assert second_tracks[0].tracker_id == first_tracks[0].tracker_id
    assert second_tracks[0].low_score_recovered is True
    assert tracker.diagnostics.low_score_recovery_count == 1
    assert tracker.diagnostics.new_track_count == 0


def test_tracking_service_uses_global_assignment_for_competing_matches() -> None:
    tracker = TrackingService(iou_threshold=0.3, max_center_distance=80.0)
    tracker.update(
        Detections(
            items=[
                Detection([0, 0, 20, 20], 0.9, 2, "car"),
                Detection([60, 0, 80, 20], 0.9, 2, "car"),
            ],
            frame_index=1,
            timestamp_sec=0.0,
        )
    )

    tracks = tracker.update(
        Detections(
            items=[
                Detection([62, 0, 82, 20], 0.9, 2, "car"),
                Detection([2, 0, 22, 20], 0.9, 2, "car"),
            ],
            frame_index=2,
            timestamp_sec=0.1,
        )
    )

    by_center_x = {round(track.center[0]): track.tracker_id for track in tracks}
    assert by_center_x[12] == 1
    assert by_center_x[72] == 2
    assert tracker.diagnostics.association_match_count == 2


def test_zone_service_counts_directional_line_crossing() -> None:
    tracker = TrackingService(iou_threshold=0.3)
    zone_service = ZoneService([ZoneConfig("main_gate", [0, 10], [40, 10])])

    frame_1 = Detections(
        items=[Detection([10, 0, 20, 8], 0.9, 2, "car")],
        frame_index=1,
        timestamp_sec=0.0,
    )
    frame_2 = Detections(
        items=[Detection([10, 12, 20, 24], 0.9, 2, "car")],
        frame_index=2,
        timestamp_sec=0.1,
    )

    zone_service.trigger(tracker.update(frame_1))
    stats = zone_service.trigger(tracker.update(frame_2))

    assert stats[0].name == "main_gate"
    assert stats[0].in_count == 1
    assert stats[0].out_count == 0


def test_zone_service_ignores_side_flip_outside_finite_counting_segment() -> None:
    tracker = TrackingService(iou_threshold=0.3)
    zone_service = ZoneService([ZoneConfig("main_gate", [0, 10], [40, 10])])

    frame_1 = Detections(
        items=[Detection([70, 0, 90, 8], 0.9, 2, "car")],
        frame_index=1,
        timestamp_sec=0.0,
    )
    frame_2 = Detections(
        items=[Detection([70, 12, 90, 24], 0.9, 2, "car")],
        frame_index=2,
        timestamp_sec=0.1,
    )

    zone_service.trigger(tracker.update(frame_1))
    stats = zone_service.trigger(tracker.update(frame_2))

    assert stats[0].in_count == 0
    assert stats[0].out_count == 0


def test_report_generator_builds_frame_and_cumulative_stats() -> None:
    generator = ReportGenerator()
    tracks = [Detection([10, 10, 30, 30], 0.9, 2, "car").to_track(tracker_id=1)]
    zone_service = ZoneService([ZoneConfig("main_gate", [0, 10], [40, 10])])

    report = generator.add_frame(
        frame_index=10,
        timestamp_sec=1.0,
        tracks=tracks,
        zone_stats=zone_service.get_stats(),
        fps=24.0,
        speeds={1: 42.5},
    )
    cumulative = generator.generate_cumulative_stats()

    assert report.active_tracks[0].speed_kmh == 42.5
    assert report.active_tracks[0].speed_confidence is None
    assert report.calibration_quality is None
    assert report.total_in == 0
    assert cumulative.total_frames == 1
    assert cumulative.total_unique_tracks == 1
    assert cumulative.avg_fps == 24.0


def test_video_processor_keeps_manual_homography_until_candidate_gate_passes() -> None:
    base = _homography_result(np.eye(3))
    candidate = [[2.0, 0.0, 0.0], [0.0, 2.0, 0.0], [0.0, 0.0, 1.0]]
    processor = SupervisionVideoProcessor(
        detector=object(),  # type: ignore[arg-type]
        adapter=object(),  # type: ignore[arg-type]
        calibration=base,
        zone=ZoneConfig("main", [0, 0], [10, 0]),
        calibration_context={
            "calibration_source": "video_manual_preset",
            "calibration_trusted": True,
            "calibration_3d_diagnostics": {
                "calibration_trusted": True,
                "homography_consistency": {"passed": True},
                "h_pixel_to_world": candidate,
            },
        },
    )

    diagnostics = processor._build_calibration_diagnostics()

    assert processor.calibration.homography_matrix[0, 0] == pytest.approx(1.0)
    assert diagnostics["runtime_homography_source"] == "planar_homography"
    assert diagnostics["selected_calibration_candidate_id"] == "manual_runtime_preset"
    rejection_reasons = diagnostics["candidate_rejection_reasons"]
    assert isinstance(rejection_reasons, dict)
    assert "vehicle_3d_prior_pnp" in rejection_reasons


def test_calibration_diagnostics_do_not_mark_raw_homography_as_undistorted() -> None:
    processor = SupervisionVideoProcessor(
        detector=object(),  # type: ignore[arg-type]
        adapter=object(),  # type: ignore[arg-type]
        calibration=_homography_result(np.eye(3)),
        zone=ZoneConfig("main", [0, 0], [10, 0]),
        calibration_context={
            "calibration_source": "video_manual_preset",
            "calibration_trusted": True,
            "camera_intrinsics": {"fx": 900.0, "fy": 900.0, "cx": 50.0, "cy": 50.0},
            "distortion_coefficients": [0.1, -0.02, 0.0, 0.0, 0.0],
        },
    )

    diagnostics = processor._build_calibration_diagnostics()

    assert diagnostics["homography_coordinate_space"] == "raw_frame"
    assert diagnostics["undistortion_applied"] is False
    assert diagnostics["undistorted_metric_profile"] is False
    assert (
        diagnostics["coordinate_space_warning"]
        == "intrinsics_present_but_homography_raw_frame"
    )
    assert diagnostics["camera_geometry_profile"]["model_reference"] == (
        "camera_geometry_profile_v1"
    )
    assert diagnostics["camera_geometry_profile"]["homography_coordinate_space"] == (
        "raw_distorted_pixel"
    )
    assert diagnostics["point_coordinate_space"] == "raw_distorted_pixel"
    assert diagnostics["metric_plane_speed_acceptance"]["model_reference"] == (
        "metric_plane_speed_acceptance_v1"
    )
    assert diagnostics["pinhole_geometry_profile"]["model_reference"] == (
        "pinhole_geometry_audit_v1"
    )
    assert diagnostics["homography_decomposition_residual"] is not None
    assert diagnostics["local_jacobian_speed_amplification_p95"] is not None
    assert diagnostics["intrinsics_consistency_status"] == "single_plane"


def test_coordinate_contract_rejects_undistorted_h_without_intrinsics() -> None:
    contract = CoordinateSpaceContract.from_context(
        {
            "homography_coordinate_space": "undistorted_pixel",
            "control_point_coordinate_space": "undistorted_pixel",
        },
        frame_width=100,
        frame_height=100,
    )

    result = contract.transform_pixel((10.0, 20.0))

    assert contract.gate_reason == "distortion_model_missing"
    assert result.pixel is None
    assert result.gate_reason == "distortion_model_missing"


def test_contact_fusion_reports_pose_stance_state() -> None:
    processor = SupervisionVideoProcessor(
        detector=object(),  # type: ignore[arg-type]
        adapter=object(),  # type: ignore[arg-type]
        calibration=_homography_result(np.eye(3)),
        zone=ZoneConfig("main", [0, 0], [10, 0]),
    )
    bbox = GroundContactPoint(
        pixel=(10.0, 20.0),
        raw_pixel=(10.0, 20.0),
        confidence=0.6,
        source="bbox_ground_contact",
        measurement_source="bbox_ground_contact",
        observation_sigma_px=4.0,
        contact_state="unknown",
    )
    pose = GroundContactPoint(
        pixel=(10.5, 19.5),
        raw_pixel=(10.5, 19.5),
        confidence=0.9,
        source="pose_ankle_ground_contact",
        measurement_source="pose_ankle_ground_contact",
        observation_sigma_px=1.0,
        contact_state="stance_foot",
    )

    fused = processor._fuse_contact_point(bbox, pose, None)

    assert fused.contact_state == "stance_foot"
    assert "pose_ankle_ground_contact" in (fused.fusion_sources or [])


def test_pedestrian_contact_state_rejects_bicycle_polluted_bbox() -> None:
    estimator = PedestrianContactStateEstimator()
    contact = GroundContactPoint(
        pixel=(15.0, 50.0),
        raw_pixel=(15.0, 50.0),
        confidence=0.9,
        source="bbox_ground_contact",
        measurement_source="bbox_ground_contact",
        contact_state="unknown",
    )

    result = estimator.assess(
        tracker_id=13,
        class_id=0,
        bbox_xyxy=[0.0, 0.0, 40.0, 50.0],
        contact_point=contact,
        timestamp_sec=1.0,
        person_bicycle_overlap=0.2,
    )

    assert result.contact_state == "bicycle_push"
    assert result.measurement_policy == "reject"
    assert result.contact_phase_probabilities["unknown"] == pytest.approx(1.0)


def test_video_processor_rejects_bev_inconsistent_observation() -> None:
    processor = SupervisionVideoProcessor(
        detector=object(),  # type: ignore[arg-type]
        adapter=object(),  # type: ignore[arg-type]
        calibration=_homography_result(np.eye(3)),
        zone=ZoneConfig("main", [0, 0], [10, 0]),
        calibration_context={
            "calibration_source": "video_manual_preset",
            "calibration_trusted": True,
        },
    )
    processor.speed_estimator._latest_records[5] = SpeedRecord(
        tracker_id=5,
        speed_kmh=36.0,
        timestamp_sec=1.0,
        world_x=10.0,
        world_y=0.0,
        velocity_x_mps=10.0,
        velocity_y_mps=0.0,
        physics_valid=True,
    )

    assert processor._bev_consistency_pass(
        tracker_id=5,
        class_id=2,
        world_position=(80.0, 0.0),
        timestamp_sec=2.0,
    ) is False


def test_identity_posterior_promotes_tracking_integrity_risk() -> None:
    track = Track(
        tracker_id=13,
        class_id=0,
        class_name="person",
        confidence=0.8,
        xyxy=[0.0, 0.0, 10.0, 30.0],
        first_seen_frame=1,
        last_seen_frame=2,
        low_score_recovered=True,
        association_quality=0.4,
    )
    integrity = TrackingIntegrityResult(
        state="suspected_id_switch",
        id_switch_risk=0.8,
        speed_frozen=True,
        rejection_reason="bev_prediction_jump",
    )

    posterior = SupervisionVideoProcessor._identity_posterior(track, integrity)

    assert posterior["model_reference"] == "tracking_identity_posterior_v5"
    assert posterior["id_switch_probability"] == pytest.approx(0.8)
    assert posterior["low_score_recovery_ratio"] == pytest.approx(1.0)


def test_video_processor_predicts_one_frame_gap_from_flow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    processor = SupervisionVideoProcessor(
        detector=object(),  # type: ignore[arg-type]
        adapter=object(),  # type: ignore[arg-type]
        calibration=_homography_result(np.eye(3)),
        zone=ZoneConfig("main", [0, 0], [10, 0]),
        calibration_context={
            "calibration_source": "video_manual_preset",
            "calibration_trusted": True,
        },
    )
    previous = Track(
        tracker_id=9,
        class_id=2,
        class_name="car",
        confidence=0.9,
        xyxy=[10.0, 10.0, 30.0, 30.0],
        first_seen_frame=1,
        last_seen_frame=1,
    )
    processor._previous_frame_image = object()
    processor._previous_track_metadata = {9: previous}
    processor._previous_track_boxes = {9: list(previous.xyxy)}
    processor._previous_contact_points = {9: (20.0, 30.0)}

    def refine_contact_point(**_: object) -> GroundContactPoint:
        return GroundContactPoint(
            pixel=(24.0, 30.0),
            raw_pixel=(24.0, 30.0),
            confidence=0.8,
            source="flow_refined_ground_contact",
            measurement_source="flow_refined_ground_contact",
        )

    monkeypatch.setattr(
        processor.optical_flow_estimator,
        "refine_contact_point",
        refine_contact_point,
    )

    predictions = processor._flow_gap_predictions([], object(), frame_index=2)

    assert len(predictions) == 1
    assert predictions[0].reconstructed is True
    assert predictions[0].xyxy == pytest.approx([14.0, 10.0, 34.0, 30.0])
