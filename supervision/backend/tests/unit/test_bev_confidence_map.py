from __future__ import annotations

import numpy as np
from domain.calibration.bev_confidence import BEVConfidenceMapBuilder
from domain.speed.view_transformer import ViewTransformer


def test_bev_confidence_map_marks_outside_polygon_as_caution_or_rejected() -> None:
    transformer = ViewTransformer(np.array([[0.1, 0, 0], [0, 0.1, 0], [0, 0, 1]]))
    confidence_map = BEVConfidenceMapBuilder(
        transformer,
        frame_width=100,
        frame_height=100,
        road_plane_polygon_world=[(2, 2), (8, 2), (8, 8), (2, 8)],
        grid_cols=4,
        grid_rows=4,
    ).build()

    levels = {cell.risk_level for cell in confidence_map.cells}

    assert "trusted" in levels
    assert "caution" in levels or "rejected" in levels


def test_high_local_scale_tail_is_rejected() -> None:
    matrix = np.array([[0.02, 0.0, 0.0], [0.0, 0.02, 0.0], [0.0, -0.009, 1.0]])
    confidence_map = BEVConfidenceMapBuilder(
        ViewTransformer(matrix),
        frame_width=100,
        frame_height=100,
        grid_cols=4,
        grid_rows=4,
    ).build()

    assert any(cell.risk_level == "rejected" for cell in confidence_map.cells)
    assert confidence_map.p95_local_scale >= confidence_map.p75_local_scale
