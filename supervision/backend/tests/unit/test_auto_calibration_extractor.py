from __future__ import annotations

import pytest
from infrastructure.cv.auto_calibration_extractor import FrameGeometryExtractor


def test_frame_geometry_extractor_detects_synthetic_road_lines() -> None:
    cv2 = pytest.importorskip("cv2")
    np = pytest.importorskip("numpy")

    image = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.line(image, (180, 470), (300, 160), (255, 255, 255), 5)
    cv2.line(image, (460, 470), (340, 160), (255, 255, 255), 5)
    cv2.line(image, (160, 360), (480, 360), (255, 255, 255), 4)

    evidence = FrameGeometryExtractor(max_lines=8, hough_threshold=35).extract_from_image(
        image,
        frame_index=0,
    )

    assert evidence.frame_width == 640
    assert evidence.frame_height == 480
    assert len(evidence.candidate_lines) >= 3
    assert any(line.kind == "frame_lane_or_road_edge" for line in evidence.candidate_lines)
    assert any(line.kind == "frame_stop_or_crosswalk_line" for line in evidence.candidate_lines)


def test_frame_geometry_evidence_serializes_candidate_lines() -> None:
    cv2 = pytest.importorskip("cv2")
    np = pytest.importorskip("numpy")

    image = np.zeros((240, 320, 3), dtype=np.uint8)
    cv2.line(image, (60, 230), (150, 40), (255, 255, 255), 4)
    cv2.line(image, (260, 230), (170, 40), (255, 255, 255), 4)

    evidence = FrameGeometryExtractor(max_lines=4, hough_threshold=25).extract_from_image(image)
    payload = evidence.to_dict()

    assert payload["candidate_line_count"] == len(evidence.candidate_lines)
    assert payload["candidate_lines"]
