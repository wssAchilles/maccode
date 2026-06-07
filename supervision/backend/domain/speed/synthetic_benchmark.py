from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from domain.motion.router import MotionRouter
from domain.speed.estimator import SpeedEstimator
from domain.speed.view_transformer import ViewTransformer


@dataclass(frozen=True)
class SyntheticSpeedScenario:
    name: str
    true_speed_kmh: float
    duration_sec: float = 8.0
    fps: float = 4.0
    pixel_noise_sigma: float = 0.0
    position_rmse_m: float = 0.05
    missing_frame_indices: frozenset[int] = field(default_factory=frozenset)
    random_seed: int = 0


@dataclass(frozen=True)
class SyntheticSpeedBenchmarkResult:
    scenario_name: str
    rmse_kmh: float
    mae_kmh: float
    coverage_ratio: float
    mean_uncertainty_kmh: float
    valid_estimate_count: int
    model_reference: str = "synthetic_homography_speed_benchmark"

    def to_dict(self) -> dict[str, object]:
        return {
            "scenario_name": self.scenario_name,
            "rmse_kmh": self.rmse_kmh,
            "mae_kmh": self.mae_kmh,
            "coverage_ratio": self.coverage_ratio,
            "mean_uncertainty_kmh": self.mean_uncertainty_kmh,
            "valid_estimate_count": self.valid_estimate_count,
            "model_reference": self.model_reference,
        }


class SyntheticSpeedBenchmarkRunner:
    def __init__(self, homography_matrix: np.ndarray | None = None) -> None:
        self.homography_matrix = (
            np.eye(3, dtype=np.float64)
            if homography_matrix is None
            else np.asarray(homography_matrix, dtype=np.float64)
        )

    def run_scenario(
        self,
        scenario: SyntheticSpeedScenario,
    ) -> SyntheticSpeedBenchmarkResult:
        if scenario.duration_sec <= 0:
            raise ValueError("duration_sec must be positive")
        if scenario.fps <= 0:
            raise ValueError("fps must be positive")
        if scenario.pixel_noise_sigma < 0:
            raise ValueError("pixel_noise_sigma must not be negative")
        rng = np.random.default_rng(scenario.random_seed)
        estimator = SpeedEstimator(
            ViewTransformer(self.homography_matrix),
            position_rmse_m=scenario.position_rmse_m,
            timestamp_uncertainty_sec=1.0 / scenario.fps,
        )
        motion_profile = MotionRouter().route_class(2)
        inverse_h = np.linalg.inv(self.homography_matrix).astype(np.float64)
        true_speed_mps = max(float(scenario.true_speed_kmh), 0.0) / 3.6
        estimates: list[float] = []
        uncertainties: list[float] = []
        covered = 0
        frame_count = int(scenario.duration_sec * scenario.fps) + 1

        for frame_index in range(frame_count):
            if frame_index in scenario.missing_frame_indices:
                continue
            timestamp_sec = frame_index / scenario.fps
            world_position = (true_speed_mps * timestamp_sec, 0.0)
            pixel = self._world_to_pixel(inverse_h, world_position)
            if scenario.pixel_noise_sigma > 0:
                noise = rng.normal(0.0, scenario.pixel_noise_sigma, size=2)
                pixel = (float(pixel[0] + noise[0]), float(pixel[1] + noise[1]))
            estimator.update(
                tracker_id=1,
                pixel_center=pixel,
                timestamp_sec=timestamp_sec,
                motion_profile=motion_profile,
                detection_confidence=0.95,
                measurement_confidence=0.95,
                pixel_sigma_px=max(scenario.pixel_noise_sigma, 0.02),
                measurement_source="synthetic_contact_point",
            )
            record = estimator.get_record(1)
            if record is None or record.speed_kmh is None:
                continue
            estimates.append(record.speed_kmh)
            if record.speed_uncertainty_kmh is not None:
                uncertainties.append(record.speed_uncertainty_kmh)
                lower = max(0.0, record.speed_kmh - record.speed_uncertainty_kmh)
                upper = record.speed_kmh + record.speed_uncertainty_kmh
                covered += int(lower <= scenario.true_speed_kmh <= upper)

        if not estimates:
            return SyntheticSpeedBenchmarkResult(
                scenario_name=scenario.name,
                rmse_kmh=0.0,
                mae_kmh=0.0,
                coverage_ratio=0.0,
                mean_uncertainty_kmh=0.0,
                valid_estimate_count=0,
            )
        errors = np.asarray(estimates, dtype=np.float64) - float(scenario.true_speed_kmh)
        return SyntheticSpeedBenchmarkResult(
            scenario_name=scenario.name,
            rmse_kmh=float(np.sqrt(np.mean(errors**2))),
            mae_kmh=float(np.mean(np.abs(errors))),
            coverage_ratio=float(covered / max(len(uncertainties), 1)),
            mean_uncertainty_kmh=(
                float(np.mean(np.asarray(uncertainties, dtype=np.float64)))
                if uncertainties
                else 0.0
            ),
            valid_estimate_count=len(estimates),
        )

    @staticmethod
    def _world_to_pixel(
        inverse_h: np.ndarray,
        world_position: tuple[float, float],
    ) -> tuple[float, float]:
        homogeneous = np.array(
            [world_position[0], world_position[1], 1.0],
            dtype=np.float64,
        )
        projected = inverse_h @ homogeneous
        projected = projected / projected[2]
        return (float(projected[0]), float(projected[1]))


def run_default_synthetic_speed_benchmark() -> list[SyntheticSpeedBenchmarkResult]:
    runner = SyntheticSpeedBenchmarkRunner()
    scenarios = [
        SyntheticSpeedScenario(
            name="clean_constant_speed",
            true_speed_kmh=36.0,
            pixel_noise_sigma=0.0,
            random_seed=3,
        ),
        SyntheticSpeedScenario(
            name="short_missing_segment",
            true_speed_kmh=28.0,
            pixel_noise_sigma=0.05,
            missing_frame_indices=frozenset({10, 11, 12}),
            random_seed=9,
        ),
        SyntheticSpeedScenario(
            name="noisy_far_field",
            true_speed_kmh=36.0,
            pixel_noise_sigma=0.35,
            position_rmse_m=0.45,
            random_seed=5,
        ),
    ]
    return [runner.run_scenario(scenario) for scenario in scenarios]
