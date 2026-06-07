from __future__ import annotations

from domain.speed.pedestrian_scale_drift import (
    PedestrianGeometrySample,
    PedestrianScaleDriftAnalyzer,
)


def test_bbox_height_shrinks_and_speed_grows_triggers_scale_drift() -> None:
    samples = [
        PedestrianGeometrySample(
            tracker_id=13,
            speed_kmh=speed,
            bbox_top=(100.0, bottom_y - height),
            bbox_bottom=(100.0, bottom_y),
            bbox_height_px=height,
            footpoint_pixel=(100.0, bottom_y),
            pixel_y=bottom_y,
            local_scale_factor=scale,
            local_scale_percentile=percentile,
            timestamp_sec=float(index),
        )
        for index, (speed, height, bottom_y, scale, percentile) in enumerate(
            [
                (7.0, 96.0, 180.0, 1.0, 0.35),
                (8.5, 88.0, 195.0, 1.2, 0.50),
                (10.5, 78.0, 210.0, 1.5, 0.65),
                (13.5, 68.0, 228.0, 1.9, 0.78),
                (16.5, 58.0, 244.0, 2.3, 0.86),
                (20.0, 50.0, 260.0, 2.8, 0.92),
            ]
        )
    ]

    result = PedestrianScaleDriftAnalyzer().analyze(samples)

    assert result.scale_drift_detected is True
    assert result.geometry_rejection_reason == "pedestrian_perspective_scale_drift"
    assert result.speed_inverse_height_correlation is not None
    assert result.speed_inverse_height_correlation >= 0.60
    assert result.recommended_speed_scale_factor is not None
    assert 0.0 < result.recommended_speed_scale_factor < 1.0
    assert result.model_reference == "pedestrian_head_foot_scale_drift_v1"


def test_stable_speed_and_height_does_not_trigger_scale_drift() -> None:
    samples = [
        PedestrianGeometrySample(
            tracker_id=4,
            speed_kmh=5.0,
            bbox_top=(50.0, 100.0),
            bbox_bottom=(50.0, 180.0 + index),
            bbox_height_px=80.0,
            footpoint_pixel=(50.0, 180.0 + index),
            pixel_y=180.0 + index,
            local_scale_factor=1.2,
            local_scale_percentile=0.40,
            timestamp_sec=float(index),
        )
        for index in range(6)
    ]

    result = PedestrianScaleDriftAnalyzer().analyze(samples)

    assert result.scale_drift_detected is False
    assert result.geometry_rejection_reason is None


def test_insufficient_samples_only_reports_model_reference() -> None:
    result = PedestrianScaleDriftAnalyzer().analyze(
        [
            PedestrianGeometrySample(
                tracker_id=9,
                speed_kmh=20.0,
                bbox_top=(20.0, 80.0),
                bbox_bottom=(20.0, 140.0),
                bbox_height_px=60.0,
                footpoint_pixel=(20.0, 140.0),
                pixel_y=140.0,
                local_scale_factor=2.5,
                local_scale_percentile=0.90,
                timestamp_sec=0.0,
            )
        ]
    )

    assert result.scale_drift_detected is False
    assert result.geometry_rejection_reason is None
    assert result.model_reference == "pedestrian_head_foot_scale_drift_v1"


def test_pose_geometry_consistency_improves_height_score() -> None:
    base = [
        PedestrianGeometrySample(
            tracker_id=2,
            speed_kmh=5.0,
            bbox_top=(40.0, 50.0),
            bbox_bottom=(40.0, 150.0 + index),
            bbox_height_px=100.0,
            footpoint_pixel=(40.0, 150.0 + index),
            pixel_y=150.0 + index,
            local_scale_factor=1.0,
            local_scale_percentile=0.30,
            timestamp_sec=float(index),
        )
        for index in range(6)
    ]
    pose = [
        PedestrianGeometrySample(
            **{
                **sample.__dict__,
                "pose_ankle_pixel": sample.footpoint_pixel,
                "pose_head_pixel": sample.bbox_top,
            }
        )
        for sample in base
    ]

    analyzer = PedestrianScaleDriftAnalyzer()
    assert analyzer.analyze(pose).height_consistency_score > analyzer.analyze(
        base
    ).height_consistency_score
