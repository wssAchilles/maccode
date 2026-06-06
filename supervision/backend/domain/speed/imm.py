from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class IMMState:
    motion_mode: str
    motion_mode_probability: float
    imm_speed_kmh: float
    mode_probabilities: dict[str, float]

    def to_dict(self) -> dict[str, object]:
        return {
            "motion_mode": self.motion_mode,
            "motion_mode_probability": self.motion_mode_probability,
            "imm_speed_kmh": self.imm_speed_kmh,
            "mode_probabilities": self.mode_probabilities,
        }


class LightweightIMMEstimator:
    """Offline model selector for CV/CA/stop/turning motion regimes."""

    def estimate(
        self,
        timestamps: list[float],
        xs: list[float],
        ys: list[float],
    ) -> list[IMMState]:
        if len(timestamps) != len(xs) or len(xs) != len(ys) or len(xs) < 2:
            return []
        t = np.asarray(timestamps, dtype=np.float64)
        x = np.asarray(xs, dtype=np.float64)
        y = np.asarray(ys, dtype=np.float64)
        vx = np.gradient(x, t, edge_order=1)
        vy = np.gradient(y, t, edge_order=1)
        speed_mps = np.linalg.norm(np.column_stack([vx, vy]), axis=1)
        speed_kmh = speed_mps * 3.6
        ax = np.gradient(vx, t, edge_order=1)
        ay = np.gradient(vy, t, edge_order=1)
        accel = np.linalg.norm(np.column_stack([ax, ay]), axis=1)
        heading = np.unwrap(np.arctan2(vy, vx))
        turn_rate = np.abs(np.gradient(heading, t, edge_order=1))
        states: list[IMMState] = []
        for index, speed in enumerate(speed_kmh):
            raw = {
                "constant_velocity": 1.0 / (1.0 + float(accel[index])),
                "constant_acceleration": min(float(accel[index]) / 3.0, 1.0),
                "near_stop": 1.0 / (1.0 + float(speed)),
                "turning_high_noise": min(float(turn_rate[index]) / 1.5, 1.0),
            }
            if speed < 1.0:
                raw["near_stop"] *= 3.0
                raw["constant_velocity"] *= 0.35
            total = max(sum(raw.values()), 1e-9)
            probabilities = {
                key: round(value / total, 6)
                for key, value in raw.items()
            }
            mode = max(probabilities, key=lambda key: probabilities[key])
            states.append(
                IMMState(
                    motion_mode=mode,
                    motion_mode_probability=float(probabilities[mode]),
                    imm_speed_kmh=float(speed),
                    mode_probabilities=probabilities,
                )
            )
        return states
