from __future__ import annotations

from domain.speed.synthetic_benchmark import (
    SyntheticSpeedBenchmarkRunner,
    SyntheticSpeedScenario,
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
