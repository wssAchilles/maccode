from __future__ import annotations

import pytest
from domain.crowd_density.models import CrowdDensityInput
from domain.crowd_density.service import CrowdDensityService


def test_crowd_density_uses_visible_roi_area_for_average_density() -> None:
    result = CrowdDensityService().analyze(
        CrowdDensityInput(
            points_m=[(1.0, 1.0), (2.0, 1.0), (3.0, 1.0), (4.0, 1.0)],
            region_name="pedestrian_density_area",
            region_width_m=12.0,
            region_length_m=45.0,
            direct_detection_count=4,
            visible_area_sqm=80.0,
        )
    )

    assert result.density_people_per_sqm == pytest.approx(0.05)
    assert result.density_field["visible_area_sqm"] == pytest.approx(80.0)
    assert result.density_field["visible_area_source"] == "configured_roi_polygon"
