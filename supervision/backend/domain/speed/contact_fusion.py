from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ContactPointObservation:
    pixel: tuple[float, float]
    source: str
    confidence: float
    sigma_px: float
    covariance_px: list[list[float]] | None = None
    enabled: bool = True


@dataclass(frozen=True)
class FusedContactPoint:
    pixel: tuple[float, float]
    confidence: float
    sources: list[str]
    weights: dict[str, float]
    covariance_px: list[list[float]]
    outlier_sources: list[str] | None = None
    innovation_score: float | None = None


class ContactPointFusion:
    """Fuse contact point observations using confidence-scaled covariance weights."""

    def fuse(self, observations: list[ContactPointObservation]) -> FusedContactPoint:
        usable = [
            observation
            for observation in observations
            if observation.enabled
            and observation.confidence > 0.0
            and observation.sigma_px > 0.0
            and np.all(np.isfinite(np.asarray(observation.pixel, dtype=np.float64)))
        ]
        if not usable:
            raise ValueError("at least one enabled contact observation is required")
        if len(usable) == 1:
            observation = usable[0]
            covariance = self._covariance(observation)
            return FusedContactPoint(
                pixel=observation.pixel,
                confidence=float(max(0.0, min(1.0, observation.confidence))),
                sources=[observation.source],
                weights={observation.source: 1.0},
                covariance_px=covariance.tolist(),
                outlier_sources=[],
                innovation_score=0.0,
            )

        usable, outlier_sources, innovation_score = self._gate_observations(usable)
        if len(usable) == 1:
            observation = usable[0]
            covariance = self._covariance(observation)
            return FusedContactPoint(
                pixel=observation.pixel,
                confidence=float(max(0.0, min(1.0, observation.confidence)) * 0.85),
                sources=[observation.source],
                weights={observation.source: 1.0},
                covariance_px=covariance.tolist(),
                outlier_sources=outlier_sources,
                innovation_score=innovation_score,
            )

        weighted_sum = np.zeros(2, dtype=np.float64)
        precision_sum = np.zeros((2, 2), dtype=np.float64)
        scalar_weights: dict[str, float] = {}
        for observation in usable:
            covariance = self._covariance(observation)
            precision = np.linalg.pinv(covariance)
            confidence = max(0.05, min(1.0, observation.confidence))
            weighted_precision = precision * confidence
            point = np.asarray(observation.pixel, dtype=np.float64)
            precision_sum += weighted_precision
            weighted_sum += weighted_precision @ point
            scalar_weights[observation.source] = (
                scalar_weights.get(observation.source, 0.0)
                + float(confidence / max(float(np.trace(covariance) / 2.0), 1e-9))
            )
        fused_covariance = np.linalg.pinv(precision_sum)
        fused_pixel = fused_covariance @ weighted_sum
        weight_total = max(sum(scalar_weights.values()), 1e-9)
        normalized_weights = {
            source: float(weight / weight_total)
            for source, weight in sorted(scalar_weights.items())
        }
        confidence = min(1.0, sum(normalized_weights.values()) / len(usable) + 0.35)
        return FusedContactPoint(
            pixel=(float(fused_pixel[0]), float(fused_pixel[1])),
            confidence=float(confidence),
            sources=list(normalized_weights.keys()),
            weights=normalized_weights,
            covariance_px=fused_covariance.astype(float).tolist(),
            outlier_sources=outlier_sources,
            innovation_score=innovation_score,
        )

    def _gate_observations(
        self,
        observations: list[ContactPointObservation],
    ) -> tuple[list[ContactPointObservation], list[str], float]:
        scores: dict[str, float] = {observation.source: 0.0 for observation in observations}
        counts: dict[str, int] = {observation.source: 0 for observation in observations}
        for left_index, left in enumerate(observations):
            for right in observations[left_index + 1:]:
                distance = self._innovation_d2(left, right)
                scores[left.source] = max(scores[left.source], distance)
                scores[right.source] = max(scores[right.source], distance)
                counts[left.source] += 1
                counts[right.source] += 1
        if not scores:
            return observations, [], 0.0
        innovation_score = max(scores.values())
        outliers = [
            source
            for source, score in scores.items()
            if score > 16.0 and counts.get(source, 0) > 0
        ]
        if len(outliers) >= len(observations):
            best = min(
                observations,
                key=lambda observation: (
                    scores.get(observation.source, 0.0),
                    -observation.confidence,
                    observation.sigma_px,
                ),
            )
            remaining_outliers = [
                source for source in outliers if source != best.source
            ]
            return [best], remaining_outliers, innovation_score
        kept = [
            observation
            for observation in observations
            if observation.source not in outliers
        ]
        return kept or observations, outliers, innovation_score

    def _innovation_d2(
        self,
        left: ContactPointObservation,
        right: ContactPointObservation,
    ) -> float:
        left_point = np.asarray(left.pixel, dtype=np.float64)
        right_point = np.asarray(right.pixel, dtype=np.float64)
        covariance = self._covariance(left) + self._covariance(right)
        delta = left_point - right_point
        return float(delta.T @ np.linalg.pinv(covariance) @ delta)

    @staticmethod
    def _covariance(observation: ContactPointObservation) -> np.ndarray:
        if observation.covariance_px is not None:
            covariance = np.asarray(observation.covariance_px, dtype=np.float64)
            if covariance.shape == (2, 2) and np.all(np.isfinite(covariance)):
                return covariance + np.eye(2, dtype=np.float64) * 1e-6
        sigma = max(float(observation.sigma_px), 1e-6)
        return np.eye(2, dtype=np.float64) * sigma**2
