from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from domain.calibration.models import CalibrationPoint

AUTO_PROVENANCE_TOKENS = (
    "agent",
    "auto",
    "visual-prior",
    "visual_prior",
    "visual prior",
    "geometry_prior",
    "opencv",
    "hough",
    "synthetic",
    "illustrative",
)

UNSURVEYED_SCALE_TOKENS = (
    "not a field survey",
    "not field surveyed",
    "visual-prior",
    "visual_prior",
    "visual prior",
    "illustrative",
)


def manual_calibration_provenance_issues(
    *,
    annotation_method: str | None,
    evidence_sources: Sequence[Any] | None,
    scale_prior: dict[str, Any] | str | None,
) -> list[str]:
    """Return issues that disqualify a calibration from trusted grid rendering."""

    issues: list[str] = []
    method = str(annotation_method or "").strip().lower()
    if method and any(token in method for token in AUTO_PROVENANCE_TOKENS):
        issues.append(f"annotation_method is not manual/survey provenance: {method}")

    for source in evidence_sources or []:
        text = str(source).strip().lower()
        if any(token in text for token in AUTO_PROVENANCE_TOKENS):
            issues.append(f"evidence source is only automatic/visual prior: {source}")

    scale_text = _scale_prior_text(scale_prior)
    if any(token in scale_text for token in UNSURVEYED_SCALE_TOKENS):
        issues.append("scale_prior explicitly says it is not a real surveyed/manual anchor")
    return issues


def has_manual_calibration_provenance(
    *,
    annotation_method: str | None,
    evidence_sources: Sequence[Any] | None,
    scale_prior: dict[str, Any] | str | None,
) -> bool:
    return not manual_calibration_provenance_issues(
        annotation_method=annotation_method,
        evidence_sources=evidence_sources,
        scale_prior=scale_prior,
    )


def validation_independent_segment_count(
    points: Sequence[CalibrationPoint],
    validation_segments: list[dict[str, Any]],
    *,
    tolerance: float = 1e-6,
) -> int:
    return sum(
        1
        for segment in validation_segments
        if _is_independent_segment(points, segment, tolerance=tolerance)
    )


def has_independent_validation_segment(
    points: Sequence[CalibrationPoint],
    validation_segments: list[dict[str, Any]],
    *,
    tolerance: float = 1e-6,
) -> bool:
    return (
        validation_independent_segment_count(
            points,
            validation_segments,
            tolerance=tolerance,
        )
        > 0
    )


def _is_independent_segment(
    points: Sequence[CalibrationPoint],
    segment: dict[str, Any],
    *,
    tolerance: float,
) -> bool:
    pixel_start = segment.get("pixel_start")
    pixel_end = segment.get("pixel_end")
    world_start = segment.get("world_start")
    world_end = segment.get("world_end")
    if not (
        _is_pair(pixel_start)
        and _is_pair(pixel_end)
        and _is_pair(world_start)
        and _is_pair(world_end)
    ):
        return False
    start_reuses_control_point = _matches_control_point(
        points,
        pixel_start,
        world_start,
        tolerance=tolerance,
    )
    end_reuses_control_point = _matches_control_point(
        points,
        pixel_end,
        world_end,
        tolerance=tolerance,
    )
    return not (start_reuses_control_point and end_reuses_control_point)


def _matches_control_point(
    points: Sequence[CalibrationPoint],
    pixel: Any,
    world: Any,
    *,
    tolerance: float,
) -> bool:
    return any(
        abs(point.pixel_x - float(pixel[0])) <= tolerance
        and abs(point.pixel_y - float(pixel[1])) <= tolerance
        and abs(point.world_x - float(world[0])) <= tolerance
        and abs(point.world_y - float(world[1])) <= tolerance
        for point in points
    )


def _is_pair(value: Any) -> bool:
    return isinstance(value, (list, tuple)) and len(value) == 2


def _scale_prior_text(scale_prior: dict[str, Any] | str | None) -> str:
    if scale_prior is None:
        return ""
    if isinstance(scale_prior, str):
        return scale_prior.lower()
    values = [
        str(scale_prior.get("kind", "")),
        str(scale_prior.get("description", "")),
    ]
    return " ".join(values).lower()
