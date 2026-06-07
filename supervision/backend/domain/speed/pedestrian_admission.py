from __future__ import annotations

from dataclasses import dataclass

from domain.calibration.models import MetricPlaneCalibration, MetricPlaneSelection
from domain.speed.ground_contact import GroundContactPoint

PEDESTRIAN_METRIC_PLANE_KINDS = {"sidewalk", "curb", "plaza", "person_corridor"}


@dataclass(frozen=True)
class PedestrianMetricAdmission:
    admitted: bool
    reason: str | None = None
    requires_explicit_plane: bool = False


def assess_pedestrian_metric_admission(
    *,
    class_id: int,
    plane_selection: MetricPlaneSelection,
    contact_point: GroundContactPoint,
    bbox_contact_contaminated: bool,
) -> PedestrianMetricAdmission:
    if class_id != 0:
        return PedestrianMetricAdmission(True)
    selected_plane = plane_selection.plane
    if selected_plane is None:
        return PedestrianMetricAdmission(
            False,
            plane_selection.reason or "person_metric_plane_required",
            requires_explicit_plane=True,
        )
    plane_reason = _pedestrian_plane_rejection_reason(selected_plane, plane_selection)
    if plane_reason is not None:
        return PedestrianMetricAdmission(
            False,
            plane_reason,
            requires_explicit_plane=True,
        )
    if bbox_contact_contaminated and not _has_non_bbox_contact(contact_point):
        return PedestrianMetricAdmission(False, "pedestrian_contact_contaminated")
    return PedestrianMetricAdmission(True)


def _pedestrian_plane_rejection_reason(
    plane: MetricPlaneCalibration,
    selection: MetricPlaneSelection,
) -> str | None:
    if selection.status == "default" or not plane.explicit_metric_plane:
        return "person_metric_plane_required"
    if plane.plane_kind not in PEDESTRIAN_METRIC_PLANE_KINDS:
        return "person_sidewalk_plane_required"
    return None


def _has_non_bbox_contact(contact_point: GroundContactPoint) -> bool:
    source = contact_point.measurement_source
    if _is_non_bbox_source(source):
        return True
    return any(_is_non_bbox_source(source) for source in contact_point.fusion_sources or [])


def _is_non_bbox_source(source: str) -> bool:
    lowered = source.lower()
    return any(token in lowered for token in ("pose", "ankle", "toe", "heel", "flow"))
