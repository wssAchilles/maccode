from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CalibratedSpeedConfidence:
    confidence: float
    bin_label: str
    proxy_low_confidence: bool
    penalty: float

    def to_dict(self) -> dict[str, object]:
        return {
            "speed_confidence_calibrated": self.confidence,
            "confidence_calibration_bin": self.bin_label,
            "proxy_low_confidence": self.proxy_low_confidence,
            "confidence_penalty": self.penalty,
        }


class SpeedConfidenceCalibrator:
    """Empirically calibrates speed confidence from existing diagnostics."""

    def calibrate(self, track: dict[str, Any]) -> CalibratedSpeedConfidence:
        base = self._bounded_float(track.get("speed_confidence"), default=0.0)
        penalty = 0.0
        penalty += self._scale_penalty(track.get("position_sigma_m"), 0.5, 3.0, 0.18)
        penalty += self._scale_penalty(track.get("local_scale_factor"), 1.0, 6.0, 0.16)
        penalty += self._scale_penalty(track.get("window_residual_m"), 0.4, 3.5, 0.14)
        penalty += self._scale_penalty(track.get("speed_uncertainty_kmh"), 5.0, 30.0, 0.20)
        penalty += self._scale_penalty(track.get("id_switch_risk"), 0.25, 1.0, 0.25)
        penalty += self._fusion_penalty(track.get("contact_fusion_confidence"))
        penalty += self._bev_penalty(track.get("bev_risk_level"))
        penalty += self._stability_penalty(track)
        calibrated = max(0.0, min(1.0, base * (1.0 - min(penalty, 0.85))))
        return CalibratedSpeedConfidence(
            confidence=calibrated,
            bin_label=self._bin_label(calibrated),
            proxy_low_confidence=self._proxy_low_confidence(track, calibrated),
            penalty=round(min(penalty, 1.0), 6),
        )

    def summarize(self, reports: list[dict[str, Any]]) -> dict[str, object]:
        total = 0
        proxy_low = 0
        bins: dict[str, int] = {}
        calibrated_values: list[float] = []
        for report in reports:
            for track in report.get("active_tracks", []):
                if not isinstance(track, dict) or track.get("speed_kmh") is None:
                    continue
                total += 1
                calibrated = self.calibrate(track)
                bins[calibrated.bin_label] = bins.get(calibrated.bin_label, 0) + 1
                proxy_low += int(calibrated.proxy_low_confidence)
                calibrated_values.append(calibrated.confidence)
        denominator = max(total, 1)
        return {
            "speed_track_count": total,
            "confidence_bins": bins,
            "proxy_low_confidence_count": proxy_low,
            "proxy_low_confidence_ratio": proxy_low / denominator,
            "avg_calibrated_confidence": (
                sum(calibrated_values) / len(calibrated_values)
                if calibrated_values
                else None
            ),
            "model_reference": "proxy_label_regression_confidence_calibration",
        }

    @staticmethod
    def _bounded_float(value: object, default: float = 0.0) -> float:
        if isinstance(value, int | float):
            return max(0.0, min(1.0, float(value)))
        return default

    @staticmethod
    def _scale_penalty(
        value: object,
        clean: float,
        poor: float,
        max_penalty: float,
    ) -> float:
        if not isinstance(value, int | float):
            return 0.0
        ratio = (float(value) - clean) / max(poor - clean, 1e-6)
        return max(0.0, min(max_penalty, ratio * max_penalty))

    @staticmethod
    def _fusion_penalty(value: object) -> float:
        if not isinstance(value, int | float):
            return 0.0
        return max(0.0, min(0.16, (0.75 - float(value)) * 0.32))

    @staticmethod
    def _bev_penalty(value: object) -> float:
        if value == "rejected":
            return 0.28
        if value == "caution":
            return 0.12
        return 0.0

    @staticmethod
    def _stability_penalty(track: dict[str, Any]) -> float:
        penalty = 0.0
        if track.get("speed_frozen") is True:
            penalty += 0.25
        if track.get("quality_label") in {"low_confidence", "rejected"}:
            penalty += 0.18
        if track.get("stability_label") == "unstable_observation":
            penalty += 0.16
        return penalty

    @staticmethod
    def _bin_label(confidence: float) -> str:
        if confidence >= 0.8:
            return "very_high"
        if confidence >= 0.6:
            return "high"
        if confidence >= 0.4:
            return "medium"
        if confidence >= 0.2:
            return "low"
        return "very_low"

    @staticmethod
    def _proxy_low_confidence(track: dict[str, Any], calibrated: float) -> bool:
        high_jump = (
            isinstance(track.get("speed_jump_p95_kmh"), int | float)
            and float(track["speed_jump_p95_kmh"]) > 18.0
        )
        high_jerk = (
            isinstance(track.get("jerk_p95_mps3"), int | float)
            and float(track["jerk_p95_mps3"]) > 12.0
        )
        high_switch = (
            isinstance(track.get("id_switch_risk"), int | float)
            and float(track["id_switch_risk"]) >= 0.75
        )
        return calibrated < 0.4 or high_jump or high_jerk or high_switch
