from __future__ import annotations

from domain.speed.synthetic_benchmark import (
    SyntheticSpeedBenchmarkRunner,
    SyntheticSpeedScenario,
    SyntheticSpeedSweepConfig,
    SyntheticSpeedSweepRunner,
    run_default_synthetic_speed_benchmark,
)


def test_clean_constant_speed_scenario_has_low_error() -> None:
    result = SyntheticSpeedBenchmarkRunner().run_scenario(
        SyntheticSpeedScenario(
            name="clean_constant_speed",
            true_speed_kmh=36.0,
            duration_sec=8.0,
            fps=4.0,
            pixel_noise_sigma=0.0,
            random_seed=3,
        )
    )

    assert result.valid_estimate_count > 10
    assert result.rmse_kmh < 2.0
    assert result.mae_kmh < 1.5


def test_noisier_far_field_scenario_increases_error_and_uncertainty() -> None:
    runner = SyntheticSpeedBenchmarkRunner()

    clean = runner.run_scenario(
        SyntheticSpeedScenario(
            name="clean",
            true_speed_kmh=36.0,
            duration_sec=8.0,
            fps=4.0,
            pixel_noise_sigma=0.0,
            random_seed=5,
        )
    )
    noisy = runner.run_scenario(
        SyntheticSpeedScenario(
            name="noisy_far_field",
            true_speed_kmh=36.0,
            duration_sec=8.0,
            fps=4.0,
            pixel_noise_sigma=0.35,
            position_rmse_m=0.45,
            random_seed=5,
        )
    )

    assert noisy.rmse_kmh > clean.rmse_kmh
    assert noisy.mean_uncertainty_kmh > clean.mean_uncertainty_kmh
    assert noisy.speed_jump_p95_kmh >= clean.speed_jump_p95_kmh


def test_short_missing_segment_still_produces_valid_estimates() -> None:
    result = SyntheticSpeedBenchmarkRunner().run_scenario(
        SyntheticSpeedScenario(
            name="short_missing_segment",
            true_speed_kmh=28.0,
            duration_sec=8.0,
            fps=4.0,
            pixel_noise_sigma=0.05,
            missing_frame_indices=frozenset({10, 11, 12}),
            random_seed=9,
        )
    )

    assert result.valid_estimate_count > 5
    assert 0.0 <= result.coverage_ratio <= 1.0


def test_default_synthetic_benchmark_returns_three_named_scenarios() -> None:
    results = run_default_synthetic_speed_benchmark()

    assert {result.scenario_name for result in results} == {
        "clean_constant_speed",
        "short_missing_segment",
        "noisy_far_field",
        "contact_point_bias",
        "weak_scale_bias",
        "short_id_switch",
        "pedestrian_receding_constant_speed_bad_homography",
        "pedestrian_receding_constant_speed_guarded",
        "pedestrian_receding_constant_speed_bbox_height_scale_drift",
        "pedestrian_receding_constant_speed_corrected_geometry",
        "pedestrian_receding_pose_ankle_optional",
        "pedestrian_lateral_motion_no_scale_drift",
    }


def test_contact_bias_increases_speed_error() -> None:
    runner = SyntheticSpeedBenchmarkRunner()

    clean = runner.run_scenario(
        SyntheticSpeedScenario(
            name="clean",
            true_speed_kmh=36.0,
            duration_sec=8.0,
            fps=4.0,
            random_seed=15,
        )
    )
    biased = runner.run_scenario(
        SyntheticSpeedScenario(
            name="contact_point_bias",
            true_speed_kmh=36.0,
            duration_sec=8.0,
            fps=4.0,
            contact_bias_px=(0.35, 0.0),
            random_seed=15,
        )
    )

    assert biased.rmse_kmh > clean.rmse_kmh


def test_scale_bias_creates_systematic_speed_error() -> None:
    result = SyntheticSpeedBenchmarkRunner().run_scenario(
        SyntheticSpeedScenario(
            name="weak_scale_bias",
            true_speed_kmh=36.0,
            duration_sec=8.0,
            fps=4.0,
            position_rmse_m=0.5,
            scale_bias_pct=0.15,
            random_seed=21,
        )
    )

    assert result.rmse_kmh > 2.0
    assert result.valid_estimate_count > 10


def test_id_switch_scenario_reports_rejections_or_jumps() -> None:
    result = SyntheticSpeedBenchmarkRunner().run_scenario(
        SyntheticSpeedScenario(
            name="short_id_switch",
            true_speed_kmh=36.0,
            duration_sec=8.0,
            fps=4.0,
            id_switch_frame_indices=frozenset({15, 16, 17}),
            random_seed=31,
        )
    )

    assert result.valid_estimate_count > 0
    assert result.rejection_ratio > 0.0 or result.speed_jump_p95_kmh > 0.0
    assert result.mean_adaptive_multiplier > 0.0


def test_pedestrian_receding_bad_homography_triggers_perspective_guard() -> None:
    result = SyntheticSpeedBenchmarkRunner().run_scenario(
        SyntheticSpeedScenario(
            name="pedestrian_receding_constant_speed_bad_homography",
            true_speed_kmh=5.0,
            duration_sec=8.0,
            fps=4.0,
            actor_class_id=0,
            trajectory_direction="receding",
            bad_perspective_scale=True,
            random_seed=41,
        )
    )

    assert result.perspective_rejection_count > 0
    assert result.far_near_speed_ratio is not None
    assert result.far_near_speed_ratio >= 1.0
    assert result.speed_scale_correlation is not None
    assert result.valid_estimate_count == 0 or result.rmse_kmh < 20.0


def test_pedestrian_bbox_height_scale_drift_suppresses_absurd_speed() -> None:
    result = SyntheticSpeedBenchmarkRunner().run_scenario(
        SyntheticSpeedScenario(
            name="pedestrian_receding_constant_speed_bbox_height_scale_drift",
            true_speed_kmh=5.0,
            duration_sec=8.0,
            fps=4.0,
            actor_class_id=0,
            trajectory_direction="receding",
            bad_perspective_scale=True,
            pedestrian_bbox_model=True,
            random_seed=61,
        )
    )

    assert result.pedestrian_scale_drift_count > 0
    assert result.suppressed_pedestrian_speed_count > 0
    assert result.speed_inverse_height_correlation is not None
    assert result.max_valid_pedestrian_speed_kmh <= 18.0


def test_pedestrian_lateral_motion_does_not_trigger_scale_drift() -> None:
    result = SyntheticSpeedBenchmarkRunner().run_scenario(
        SyntheticSpeedScenario(
            name="pedestrian_lateral_motion_no_scale_drift",
            true_speed_kmh=5.0,
            actor_class_id=0,
            trajectory_direction="x",
            pedestrian_bbox_model=True,
            random_seed=71,
        )
    )

    assert result.pedestrian_scale_drift_count == 0
    assert result.max_valid_pedestrian_speed_kmh <= 18.0


def test_synthetic_sweep_returns_parameter_combination_count() -> None:
    config = SyntheticSpeedSweepConfig(
        pixel_noise_sigmas=(0.0, 0.5),
        scale_bias_pcts=(0.0, 0.15),
        missing_ratios=(0.0,),
        id_switch_lengths=(0, 2),
        random_seeds=(3, 7),
    )

    sweep = SyntheticSpeedSweepRunner().run(config)

    assert sweep.summary.scenario_count == 16
    assert len(sweep.results) == 16
    assert sweep.to_dict()["scenario_count"] == 16


def test_synthetic_sweep_top_failures_are_sorted_by_rmse() -> None:
    sweep = SyntheticSpeedSweepRunner().run(
        SyntheticSpeedSweepConfig(
            pixel_noise_sigmas=(0.0, 0.8),
            scale_bias_pcts=(0.0, 0.2),
            missing_ratios=(0.0,),
            id_switch_lengths=(0,),
            random_seeds=(3,),
        )
    )

    top_failures = sweep.top_failures(limit=3)
    rmse_values = [item.rmse_kmh for item in top_failures]

    assert rmse_values == sorted(rmse_values, reverse=True)
    assert sweep.summary.worst_case_scenario in {
        result.scenario_name for result in sweep.results
    }


def test_synthetic_sweep_pixel_noise_and_scale_bias_increase_error() -> None:
    sweep = SyntheticSpeedSweepRunner().run(
        SyntheticSpeedSweepConfig(
            pixel_noise_sigmas=(0.0, 0.8),
            scale_bias_pcts=(0.0, 0.2),
            missing_ratios=(0.0,),
            id_switch_lengths=(0,),
            random_seeds=(3, 7),
        )
    )

    clean_noise_rmse = [
        result.rmse_kmh
        for result in sweep.results
        if "noise_0.00" in result.scenario_name
    ]
    high_noise_rmse = [
        result.rmse_kmh
        for result in sweep.results
        if "noise_0.80" in result.scenario_name
    ]
    zero_scale_rmse = [
        result.rmse_kmh
        for result in sweep.results
        if "scale_0.00" in result.scenario_name
    ]
    biased_scale_rmse = [
        result.rmse_kmh
        for result in sweep.results
        if "scale_0.20" in result.scenario_name
    ]

    assert sum(high_noise_rmse) / len(high_noise_rmse) >= sum(clean_noise_rmse) / len(
        clean_noise_rmse
    )
    assert sum(biased_scale_rmse) / len(biased_scale_rmse) > sum(zero_scale_rmse) / len(
        zero_scale_rmse
    )
