from __future__ import annotations

from dataclasses import dataclass, field
from itertools import product
from typing import Literal

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
    bbox_jitter_px: float = 0.0
    contact_bias_px: tuple[float, float] = (0.0, 0.0)
    scale_bias_pct: float = 0.0
    id_switch_frame_indices: frozenset[int] = field(default_factory=frozenset)
    perspective_strength: float = 0.0
    actor_class_id: int = 2
    trajectory_direction: Literal["x", "y", "receding"] = "x"
    bad_perspective_scale: bool = False
    pedestrian_bbox_model: bool = False
    pose_geometry_available: bool = False
    random_seed: int = 0


@dataclass(frozen=True)
class SyntheticSpeedBenchmarkResult:
    scenario_name: str
    rmse_kmh: float
    mae_kmh: float
    coverage_ratio: float
    mean_uncertainty_kmh: float
    valid_estimate_count: int
    speed_jump_p95_kmh: float = 0.0
    rejection_ratio: float = 0.0
    mean_adaptive_multiplier: float = 0.0
    far_near_speed_ratio: float | None = None
    speed_scale_correlation: float | None = None
    perspective_rejection_count: int = 0
    pedestrian_scale_drift_count: int = 0
    speed_inverse_height_correlation: float | None = None
    suppressed_pedestrian_speed_count: int = 0
    max_valid_pedestrian_speed_kmh: float = 0.0
    model_reference: str = "synthetic_homography_speed_benchmark"

    def to_dict(self) -> dict[str, object]:
        return {
            "scenario_name": self.scenario_name,
            "rmse_kmh": self.rmse_kmh,
            "mae_kmh": self.mae_kmh,
            "coverage_ratio": self.coverage_ratio,
            "mean_uncertainty_kmh": self.mean_uncertainty_kmh,
            "valid_estimate_count": self.valid_estimate_count,
            "speed_jump_p95_kmh": self.speed_jump_p95_kmh,
            "rejection_ratio": self.rejection_ratio,
            "mean_adaptive_multiplier": self.mean_adaptive_multiplier,
            "far_near_speed_ratio": self.far_near_speed_ratio,
            "speed_scale_correlation": self.speed_scale_correlation,
            "perspective_rejection_count": self.perspective_rejection_count,
            "pedestrian_scale_drift_count": self.pedestrian_scale_drift_count,
            "speed_inverse_height_correlation": self.speed_inverse_height_correlation,
            "suppressed_pedestrian_speed_count": self.suppressed_pedestrian_speed_count,
            "max_valid_pedestrian_speed_kmh": self.max_valid_pedestrian_speed_kmh,
            "model_reference": self.model_reference,
        }


@dataclass(frozen=True)
class SyntheticSpeedSweepConfig:
    pixel_noise_sigmas: tuple[float, ...] = (0.0, 0.2, 0.5, 1.0)
    scale_bias_pcts: tuple[float, ...] = (-0.15, 0.0, 0.15)
    missing_ratios: tuple[float, ...] = (0.0, 0.15, 0.35)
    id_switch_lengths: tuple[int, ...] = (0, 2, 5)
    random_seeds: tuple[int, ...] = (3, 7, 11)


@dataclass(frozen=True)
class SyntheticSpeedSweepSummary:
    scenario_count: int
    mean_rmse_kmh: float
    p95_rmse_kmh: float
    worst_case_rmse_kmh: float
    worst_case_scenario: str
    mean_coverage_ratio: float
    mean_rejection_ratio: float
    mean_speed_jump_p95_kmh: float
    model_reference: str = "synthetic_speed_parameter_sweep_v1"

    def to_dict(self) -> dict[str, object]:
        return {
            "scenario_count": self.scenario_count,
            "mean_rmse_kmh": self.mean_rmse_kmh,
            "p95_rmse_kmh": self.p95_rmse_kmh,
            "worst_case_rmse_kmh": self.worst_case_rmse_kmh,
            "worst_case_scenario": self.worst_case_scenario,
            "mean_coverage_ratio": self.mean_coverage_ratio,
            "mean_rejection_ratio": self.mean_rejection_ratio,
            "mean_speed_jump_p95_kmh": self.mean_speed_jump_p95_kmh,
            "model_reference": self.model_reference,
        }


@dataclass(frozen=True)
class SyntheticSpeedSweepResult:
    summary: SyntheticSpeedSweepSummary
    results: list[SyntheticSpeedBenchmarkResult]

    def top_failures(self, limit: int = 5) -> list[SyntheticSpeedBenchmarkResult]:
        return sorted(self.results, key=lambda result: result.rmse_kmh, reverse=True)[
            : max(limit, 0)
        ]

    def to_dict(self) -> dict[str, object]:
        return {
            "summary": self.summary.to_dict(),
            "top_failures": [result.to_dict() for result in self.top_failures()],
            "scenario_count": self.summary.scenario_count,
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
        if scenario.bbox_jitter_px < 0:
            raise ValueError("bbox_jitter_px must not be negative")
        rng = np.random.default_rng(scenario.random_seed)
        true_homography = self._scenario_homography(
            self.homography_matrix,
            scenario.perspective_strength,
        )
        estimator_homography = true_homography.copy()
        if scenario.bad_perspective_scale:
            estimator_homography[2, 1] -= 0.035
        if scenario.scale_bias_pct != 0.0:
            scale = max(0.01, 1.0 + float(scenario.scale_bias_pct))
            estimator_homography[0, :] *= scale
            estimator_homography[1, :] *= scale
        estimator = SpeedEstimator(
            ViewTransformer(estimator_homography),
            position_rmse_m=scenario.position_rmse_m,
            timestamp_uncertainty_sec=1.0 / scenario.fps,
        )
        motion_profile = MotionRouter().route_class(scenario.actor_class_id)
        inverse_h = np.linalg.inv(true_homography).astype(np.float64)
        true_speed_mps = max(float(scenario.true_speed_kmh), 0.0) / 3.6
        estimates: list[float] = []
        uncertainties: list[float] = []
        adaptive_multipliers: list[float] = []
        far_near_speed_ratio: float | None = None
        speed_scale_correlation: float | None = None
        perspective_rejection_count = 0
        pedestrian_scale_drift_count = 0
        speed_inverse_height_correlation: float | None = None
        suppressed_pedestrian_speed_count = 0
        max_valid_pedestrian_speed_kmh = 0.0
        covered = 0
        attempted_frames = 0
        frame_count = int(scenario.duration_sec * scenario.fps) + 1

        for frame_index in range(frame_count):
            if frame_index in scenario.missing_frame_indices:
                continue
            attempted_frames += 1
            timestamp_sec = frame_index / scenario.fps
            world_position = self._world_position(
                true_speed_mps,
                timestamp_sec,
                scenario.trajectory_direction,
            )
            pixel = self._world_to_pixel(inverse_h, world_position)
            if scenario.pixel_noise_sigma > 0:
                noise = rng.normal(0.0, scenario.pixel_noise_sigma, size=2)
                pixel = (float(pixel[0] + noise[0]), float(pixel[1] + noise[1]))
            if scenario.bbox_jitter_px > 0:
                jitter = rng.normal(0.0, scenario.bbox_jitter_px, size=2)
                pixel = (float(pixel[0] + jitter[0]), float(pixel[1] + jitter[1]))
            if scenario.contact_bias_px != (0.0, 0.0):
                progress_factor = 1.0 + 0.04 * frame_index
                pixel = (
                    float(pixel[0] + scenario.contact_bias_px[0] * progress_factor),
                    float(pixel[1] + scenario.contact_bias_px[1] * progress_factor),
                )
            bbox_xyxy, bbox_height, pose_ankle, pose_head = self._pedestrian_bbox_geometry(
                pixel,
                frame_index,
                frame_count,
                scenario,
            )
            tracker_id = 99 if frame_index in scenario.id_switch_frame_indices else 1
            estimator.update(
                tracker_id=tracker_id,
                pixel_center=pixel,
                timestamp_sec=timestamp_sec,
                motion_profile=motion_profile,
                detection_confidence=0.95,
                measurement_confidence=0.95,
                pixel_sigma_px=max(
                    scenario.pixel_noise_sigma,
                    scenario.bbox_jitter_px,
                    0.02,
                ),
                measurement_source="synthetic_contact_point",
                local_scale_percentile=(
                    min(0.99, frame_index / max(frame_count - 1, 1))
                    if scenario.trajectory_direction == "receding"
                    else None
                ),
                bbox_xyxy=bbox_xyxy,
                bbox_height_px=bbox_height,
                pose_ankle_pixel=pose_ankle,
                pose_head_pixel=pose_head,
            )
            record = estimator.get_record(tracker_id)
            if record is None or record.speed_kmh is None:
                if record is not None:
                    far_near_speed_ratio = (
                        record.far_near_speed_ratio
                        if record.far_near_speed_ratio is not None
                        else far_near_speed_ratio
                    )
                    speed_scale_correlation = (
                        record.speed_scale_correlation
                        if record.speed_scale_correlation is not None
                        else speed_scale_correlation
                    )
                    perspective_rejection_count += int(
                        record.perspective_speed_inflation_detected
                        or record.rejection_reason == "perspective_speed_inflation"
                    )
                    pedestrian_scale_drift_count += int(
                        record.pedestrian_scale_drift_detected
                    )
                    suppressed_pedestrian_speed_count += int(
                        record.rejection_reason == "pedestrian_perspective_scale_drift"
                    )
                    speed_inverse_height_correlation = (
                        record.speed_inverse_height_correlation
                        if record.speed_inverse_height_correlation is not None
                        else speed_inverse_height_correlation
                    )
                if (
                    record is not None
                    and record.adaptive_measurement_noise_multiplier is not None
                ):
                    adaptive_multipliers.append(record.adaptive_measurement_noise_multiplier)
                continue
            estimates.append(record.speed_kmh)
            far_near_speed_ratio = (
                record.far_near_speed_ratio
                if record.far_near_speed_ratio is not None
                else far_near_speed_ratio
            )
            speed_scale_correlation = (
                record.speed_scale_correlation
                if record.speed_scale_correlation is not None
                else speed_scale_correlation
            )
            perspective_rejection_count += int(record.perspective_speed_inflation_detected)
            pedestrian_scale_drift_count += int(record.pedestrian_scale_drift_detected)
            suppressed_pedestrian_speed_count += int(
                record.rejection_reason == "pedestrian_perspective_scale_drift"
            )
            speed_inverse_height_correlation = (
                record.speed_inverse_height_correlation
                if record.speed_inverse_height_correlation is not None
                else speed_inverse_height_correlation
            )
            if scenario.actor_class_id == 0:
                max_valid_pedestrian_speed_kmh = max(
                    max_valid_pedestrian_speed_kmh,
                    float(record.speed_kmh),
                )
            if record.adaptive_measurement_noise_multiplier is not None:
                adaptive_multipliers.append(record.adaptive_measurement_noise_multiplier)
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
                rejection_ratio=1.0 if attempted_frames else 0.0,
                far_near_speed_ratio=far_near_speed_ratio,
                speed_scale_correlation=speed_scale_correlation,
                perspective_rejection_count=perspective_rejection_count,
                pedestrian_scale_drift_count=pedestrian_scale_drift_count,
                speed_inverse_height_correlation=speed_inverse_height_correlation,
                suppressed_pedestrian_speed_count=suppressed_pedestrian_speed_count,
                max_valid_pedestrian_speed_kmh=max_valid_pedestrian_speed_kmh,
            )
        errors = np.asarray(estimates, dtype=np.float64) - float(scenario.true_speed_kmh)
        speed_jumps = np.abs(np.diff(np.asarray(estimates, dtype=np.float64)))
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
            speed_jump_p95_kmh=(
                float(np.percentile(speed_jumps, 95)) if speed_jumps.size else 0.0
            ),
            rejection_ratio=float(
                max(0.0, 1.0 - (len(estimates) / max(attempted_frames, 1))),
            ),
            mean_adaptive_multiplier=(
                float(np.mean(np.asarray(adaptive_multipliers, dtype=np.float64)))
                if adaptive_multipliers
                else 0.0
            ),
            far_near_speed_ratio=far_near_speed_ratio,
            speed_scale_correlation=speed_scale_correlation,
            perspective_rejection_count=perspective_rejection_count,
            pedestrian_scale_drift_count=pedestrian_scale_drift_count,
            speed_inverse_height_correlation=speed_inverse_height_correlation,
            suppressed_pedestrian_speed_count=suppressed_pedestrian_speed_count,
            max_valid_pedestrian_speed_kmh=max_valid_pedestrian_speed_kmh,
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

    @staticmethod
    def _world_position(
        speed_mps: float,
        timestamp_sec: float,
        direction: Literal["x", "y", "receding"],
    ) -> tuple[float, float]:
        if direction in {"y", "receding"}:
            return (0.0, speed_mps * timestamp_sec)
        return (speed_mps * timestamp_sec, 0.0)

    @staticmethod
    def _pedestrian_bbox_geometry(
        footpoint: tuple[float, float],
        frame_index: int,
        frame_count: int,
        scenario: SyntheticSpeedScenario,
    ) -> tuple[
        list[float] | None,
        float | None,
        tuple[float, float] | None,
        tuple[float, float] | None,
    ]:
        if scenario.actor_class_id != 0 or not scenario.pedestrian_bbox_model:
            return None, None, None, None
        progress = frame_index / max(frame_count - 1, 1)
        if scenario.trajectory_direction == "receding":
            height = max(28.0, 108.0 * (1.0 - 0.55 * progress))
        else:
            height = 92.0
        width = max(16.0, height * 0.34)
        x, y = footpoint
        bbox = [
            float(x - width / 2.0),
            float(y - height),
            float(x + width / 2.0),
            float(y),
        ]
        pose_ankle = footpoint if scenario.pose_geometry_available else None
        pose_head = (float(x), float(y - height)) if scenario.pose_geometry_available else None
        return bbox, float(height), pose_ankle, pose_head

    @staticmethod
    def _scenario_homography(
        homography_matrix: np.ndarray,
        perspective_strength: float,
    ) -> np.ndarray:
        homography = np.asarray(homography_matrix, dtype=np.float64).copy()
        if perspective_strength != 0.0:
            homography[2, 0] += float(perspective_strength)
        return homography


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
        SyntheticSpeedScenario(
            name="contact_point_bias",
            true_speed_kmh=36.0,
            contact_bias_px=(0.35, 0.0),
            random_seed=15,
        ),
        SyntheticSpeedScenario(
            name="weak_scale_bias",
            true_speed_kmh=36.0,
            scale_bias_pct=0.15,
            random_seed=21,
        ),
        SyntheticSpeedScenario(
            name="short_id_switch",
            true_speed_kmh=36.0,
            id_switch_frame_indices=frozenset({15, 16, 17}),
            random_seed=31,
        ),
        SyntheticSpeedScenario(
            name="pedestrian_receding_constant_speed_bad_homography",
            true_speed_kmh=5.0,
            actor_class_id=0,
            trajectory_direction="receding",
            bad_perspective_scale=True,
            random_seed=41,
        ),
        SyntheticSpeedScenario(
            name="pedestrian_receding_constant_speed_guarded",
            true_speed_kmh=5.0,
            actor_class_id=0,
            trajectory_direction="receding",
            bad_perspective_scale=True,
            random_seed=43,
        ),
        SyntheticSpeedScenario(
            name="pedestrian_receding_constant_speed_bbox_height_scale_drift",
            true_speed_kmh=5.0,
            actor_class_id=0,
            trajectory_direction="receding",
            bad_perspective_scale=True,
            pedestrian_bbox_model=True,
            random_seed=61,
        ),
        SyntheticSpeedScenario(
            name="pedestrian_receding_constant_speed_corrected_geometry",
            true_speed_kmh=5.0,
            actor_class_id=0,
            trajectory_direction="receding",
            pedestrian_bbox_model=True,
            random_seed=63,
        ),
        SyntheticSpeedScenario(
            name="pedestrian_receding_pose_ankle_optional",
            true_speed_kmh=5.0,
            actor_class_id=0,
            trajectory_direction="receding",
            bad_perspective_scale=True,
            pedestrian_bbox_model=True,
            pose_geometry_available=True,
            random_seed=67,
        ),
        SyntheticSpeedScenario(
            name="pedestrian_lateral_motion_no_scale_drift",
            true_speed_kmh=5.0,
            actor_class_id=0,
            trajectory_direction="x",
            pedestrian_bbox_model=True,
            random_seed=71,
        ),
    ]
    return [runner.run_scenario(scenario) for scenario in scenarios]


class SyntheticSpeedSweepRunner:
    def __init__(self, homography_matrix: np.ndarray | None = None) -> None:
        self.benchmark_runner = SyntheticSpeedBenchmarkRunner(homography_matrix)

    def run(self, config: SyntheticSpeedSweepConfig | None = None) -> SyntheticSpeedSweepResult:
        config = config or SyntheticSpeedSweepConfig()
        results = [
            self.benchmark_runner.run_scenario(scenario)
            for scenario in self._scenarios(config)
        ]
        return SyntheticSpeedSweepResult(
            summary=self._summary(results),
            results=results,
        )

    def _scenarios(self, config: SyntheticSpeedSweepConfig) -> list[SyntheticSpeedScenario]:
        scenarios: list[SyntheticSpeedScenario] = []
        for noise, scale_bias, missing_ratio, switch_length, seed in product(
            config.pixel_noise_sigmas,
            config.scale_bias_pcts,
            config.missing_ratios,
            config.id_switch_lengths,
            config.random_seeds,
        ):
            scenarios.append(
                SyntheticSpeedScenario(
                    name=(
                        f"sweep_noise_{noise:.2f}_scale_{scale_bias:.2f}_"
                        f"missing_{missing_ratio:.2f}_switch_{switch_length}_seed_{seed}"
                    ),
                    true_speed_kmh=36.0,
                    pixel_noise_sigma=float(noise),
                    scale_bias_pct=float(scale_bias),
                    missing_frame_indices=self._missing_indices(float(missing_ratio)),
                    id_switch_frame_indices=self._id_switch_indices(int(switch_length)),
                    random_seed=int(seed),
                )
            )
        return scenarios

    @staticmethod
    def _missing_indices(missing_ratio: float, frame_count: int = 33) -> frozenset[int]:
        count = max(0, min(frame_count - 1, int(round(frame_count * missing_ratio))))
        if count == 0:
            return frozenset()
        start = max(1, (frame_count - count) // 2)
        return frozenset(range(start, start + count))

    @staticmethod
    def _id_switch_indices(switch_length: int, frame_count: int = 33) -> frozenset[int]:
        if switch_length <= 0:
            return frozenset()
        start = max(1, frame_count // 2 - switch_length // 2)
        return frozenset(range(start, min(start + switch_length, frame_count)))

    @staticmethod
    def _summary(results: list[SyntheticSpeedBenchmarkResult]) -> SyntheticSpeedSweepSummary:
        if not results:
            return SyntheticSpeedSweepSummary(
                scenario_count=0,
                mean_rmse_kmh=0.0,
                p95_rmse_kmh=0.0,
                worst_case_rmse_kmh=0.0,
                worst_case_scenario="",
                mean_coverage_ratio=0.0,
                mean_rejection_ratio=0.0,
                mean_speed_jump_p95_kmh=0.0,
            )
        rmse = np.asarray([result.rmse_kmh for result in results], dtype=np.float64)
        worst = max(results, key=lambda result: result.rmse_kmh)
        return SyntheticSpeedSweepSummary(
            scenario_count=len(results),
            mean_rmse_kmh=float(np.mean(rmse)),
            p95_rmse_kmh=float(np.percentile(rmse, 95)),
            worst_case_rmse_kmh=float(worst.rmse_kmh),
            worst_case_scenario=worst.scenario_name,
            mean_coverage_ratio=float(np.mean([result.coverage_ratio for result in results])),
            mean_rejection_ratio=float(np.mean([result.rejection_ratio for result in results])),
            mean_speed_jump_p95_kmh=float(
                np.mean([result.speed_jump_p95_kmh for result in results])
            ),
        )
