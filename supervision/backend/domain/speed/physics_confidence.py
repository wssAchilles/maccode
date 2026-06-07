from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PhysicsConfidence:
    physics_confidence: float
    calibration_confidence: float
    contact_confidence: float
    tracking_confidence: float
    occlusion_confidence: float
    dynamics_confidence: float
    confidence_rejection_reason: str | None

    def to_record_fields(self) -> dict[str, float | str | None]:
        return {
            "physics_confidence": self.physics_confidence,
            "calibration_confidence": self.calibration_confidence,
            "contact_confidence": self.contact_confidence,
            "tracking_confidence": self.tracking_confidence,
            "occlusion_confidence": self.occlusion_confidence,
            "dynamics_confidence": self.dynamics_confidence,
            "confidence_rejection_reason": self.confidence_rejection_reason,
        }


class PhysicsConfidenceModel:
    """Combines geometry, contact, tracking, occlusion, and dynamics evidence."""

    def score(
        self,
        *,
        calibration_rmse_m: float | None = None,
        validation_error_px: float | None = None,
        condition_number: float | None = None,
        local_scale_factor: float | None = None,
        measurement_confidence: float | None = None,
        contact_source: str | None = None,
        contact_fusion_confidence: float | None = None,
        id_switch_risk: float | None = None,
        tracking_integrity_state: str | None = None,
        speed_frozen: bool = False,
        quality_label: str | None = None,
        speed_uncertainty_kmh: float | None = None,
        speed_cv: float | None = None,
        max_speed_jump_kmh: float | None = None,
        acceleration_mps2: float | None = None,
        innovation_nis: float | None = None,
        speed_geometry_diagnostics: dict[str, object] | None = None,
    ) -> PhysicsConfidence:
        calibration = self._calibration_confidence(
            calibration_rmse_m,
            validation_error_px,
            condition_number,
            local_scale_factor,
        )
        contact = self._contact_confidence(
            measurement_confidence,
            contact_source,
            contact_fusion_confidence,
            speed_geometry_diagnostics,
        )
        tracking = self._tracking_confidence(
            id_switch_risk,
            tracking_integrity_state,
            speed_frozen,
            innovation_nis,
        )
        occlusion = self._occlusion_confidence(speed_geometry_diagnostics)
        dynamics = self._dynamics_confidence(
            quality_label,
            speed_uncertainty_kmh,
            speed_cv,
            max_speed_jump_kmh,
            acceleration_mps2,
        )
        total = calibration * contact * tracking * occlusion * dynamics
        factors = {
            "calibration_confidence": calibration,
            "contact_confidence": contact,
            "tracking_confidence": tracking,
            "occlusion_confidence": occlusion,
            "dynamics_confidence": dynamics,
        }
        weakest_name, weakest_value = min(factors.items(), key=lambda item: item[1])
        reason = weakest_name if total < 0.4 or weakest_value < 0.55 else None
        return PhysicsConfidence(
            physics_confidence=round(max(0.0, min(1.0, total)), 6),
            calibration_confidence=round(calibration, 6),
            contact_confidence=round(contact, 6),
            tracking_confidence=round(tracking, 6),
            occlusion_confidence=round(occlusion, 6),
            dynamics_confidence=round(dynamics, 6),
            confidence_rejection_reason=reason,
        )

    @staticmethod
    def _calibration_confidence(
        rmse_m: float | None,
        validation_px: float | None,
        condition_number: float | None,
        local_scale_factor: float | None,
    ) -> float:
        confidence = 1.0
        confidence *= 1.0 - PhysicsConfidenceModel._ramp(rmse_m, 0.15, 1.5) * 0.45
        confidence *= 1.0 - PhysicsConfidenceModel._ramp(validation_px, 8.0, 40.0) * 0.25
        confidence *= 1.0 - PhysicsConfidenceModel._ramp(condition_number, 100.0, 5000.0) * 0.15
        confidence *= 1.0 - PhysicsConfidenceModel._ramp(local_scale_factor, 1.5, 6.0) * 0.35
        return max(0.05, min(1.0, confidence))

    @staticmethod
    def _contact_confidence(
        measurement_confidence: float | None,
        contact_source: str | None,
        contact_fusion_confidence: float | None,
        diagnostics: dict[str, object] | None,
    ) -> float:
        confidence = PhysicsConfidenceModel._bounded(measurement_confidence, 0.65)
        if contact_fusion_confidence is not None:
            confidence = min(
                confidence,
                PhysicsConfidenceModel._bounded(contact_fusion_confidence, 0.65),
            )
        source = (contact_source or "").lower()
        if "pose" in source or "ankle" in source or "toe" in source or "heel" in source:
            source_factor = 1.0
        elif "flow" in source or "optical" in source:
            source_factor = 0.82
        elif "bbox" in source:
            source_factor = 0.58
        else:
            source_factor = 0.72
        if PhysicsConfidenceModel._flag(diagnostics, "bbox_contact_contaminated"):
            source_factor *= 0.45
        return max(0.05, min(1.0, confidence * source_factor))

    @staticmethod
    def _tracking_confidence(
        id_switch_risk: float | None,
        integrity_state: str | None,
        speed_frozen: bool,
        innovation_nis: float | None,
    ) -> float:
        confidence = 1.0 - PhysicsConfidenceModel._bounded(id_switch_risk, 0.0) * 0.65
        if speed_frozen:
            confidence *= 0.62
        state = (integrity_state or "").lower()
        if any(token in state for token in ("switch", "fragment", "lost", "relinked")):
            confidence *= 0.55
        confidence *= 1.0 - PhysicsConfidenceModel._ramp(innovation_nis, 4.0, 9.21) * 0.45
        return max(0.05, min(1.0, confidence))

    @staticmethod
    def _occlusion_confidence(diagnostics: dict[str, object] | None) -> float:
        if not diagnostics:
            return 0.9
        confidence = 1.0
        for key in (
            "occluded",
            "bbox_contact_contaminated",
            "pedestrian_contact_contaminated",
            "plane_transition_geometry_invalid",
        ):
            if PhysicsConfidenceModel._flag(diagnostics, key):
                confidence *= 0.62
        return max(0.05, min(1.0, confidence))

    @staticmethod
    def _dynamics_confidence(
        quality_label: str | None,
        uncertainty_kmh: float | None,
        speed_cv: float | None,
        max_jump_kmh: float | None,
        acceleration_mps2: float | None,
    ) -> float:
        confidence = 1.0
        confidence *= 1.0 - PhysicsConfidenceModel._ramp(uncertainty_kmh, 4.0, 24.0) * 0.45
        confidence *= 1.0 - PhysicsConfidenceModel._ramp(speed_cv, 0.18, 0.55) * 0.4
        confidence *= 1.0 - PhysicsConfidenceModel._ramp(max_jump_kmh, 4.0, 20.0) * 0.35
        confidence *= 1.0 - PhysicsConfidenceModel._ramp(acceleration_mps2, 1.8, 7.0) * 0.3
        if quality_label in {"low_confidence", "rejected", "geometry_invalid"}:
            confidence *= 0.55
        if quality_label == "warming_up":
            confidence *= 0.65
        return max(0.05, min(1.0, confidence))

    @staticmethod
    def _bounded(value: float | None, default: float) -> float:
        if value is None:
            return default
        return max(0.0, min(1.0, float(value)))

    @staticmethod
    def _ramp(value: float | None, clean: float, poor: float) -> float:
        if value is None:
            return 0.0
        ratio = (abs(float(value)) - clean) / max(poor - clean, 1e-6)
        return max(0.0, min(1.0, ratio))

    @staticmethod
    def _flag(diagnostics: dict[str, object] | None, key: str) -> bool:
        if not diagnostics:
            return False
        value = diagnostics.get(key)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in {"true", "yes", "1", key}
        flags = diagnostics.get("flags")
        return isinstance(flags, list) and key in flags
