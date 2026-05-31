from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/mpl")

import cv2
import numpy as np
from domain.calibration.models import CalibrationPoint, HomographyGrid
from domain.calibration.service import CalibrationService
from domain.calibration.validation import (
    manual_calibration_provenance_issues,
    validation_independent_segment_count,
)

from scripts.analyze_real_videos import (
    CalibrationPresetCatalog,
    build_calibration,
    build_camera_profile_calibration,
    inspect_video,
    is_trusted_manual_calibration,
    load_calibration_presets,
    load_camera_profiles,
    match_camera_profile,
    profile_for_clip,
    validation_segment_max_error_px,
)

GOLDEN_CLIPS = [
    "026_complex_signal_day_wide_0115s_30s.mp4",
    "042_pedestrian_crowd_high_view_0270s_30s.mp4",
    "054_dense_city_traffic_4k_elevated_0030s_30s.mp4",
    "058_dense_city_traffic_4k_elevated_0150s_30s.mp4",
]


def read_video_frame(video_path: Path, frame_index: int) -> np.ndarray:
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise ValueError(f"could not open video: {video_path}")
    try:
        capture.set(cv2.CAP_PROP_POS_FRAMES, max(frame_index - 1, 0))
        ok, frame = capture.read()
        if not ok:
            raise ValueError(f"could not read frame {frame_index} from video: {video_path}")
        return frame
    finally:
        capture.release()


def world_to_pixel(
    inverse_homography: np.ndarray,
    point: tuple[float, float],
) -> tuple[int, int]:
    projected = inverse_homography @ np.array([point[0], point[1], 1.0], dtype=float)
    projected = projected / projected[2]
    return (int(round(float(projected[0]))), int(round(float(projected[1]))))


def draw_dashed_line(
    frame: np.ndarray,
    start: tuple[int, int],
    end: tuple[int, int],
    color: tuple[int, int, int],
    thickness: int = 2,
    dash_length: int = 18,
    gap_length: int = 12,
) -> None:
    x1, y1 = start
    x2, y2 = end
    distance = float(((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5)
    if distance <= 0:
        return
    dx = (x2 - x1) / distance
    dy = (y2 - y1) / distance
    cursor = 0.0
    while cursor < distance:
        dash_end = min(cursor + dash_length, distance)
        p1 = (int(round(x1 + dx * cursor)), int(round(y1 + dy * cursor)))
        p2 = (int(round(x1 + dx * dash_end)), int(round(y1 + dy * dash_end)))
        cv2.line(frame, p1, p2, color, thickness, cv2.LINE_AA)
        cursor += dash_length + gap_length


def draw_text_panel(frame: np.ndarray, lines: list[str]) -> None:
    width = min(frame.shape[1] - 24, 860)
    height = 34 + 24 * len(lines)
    overlay = frame.copy()
    cv2.rectangle(overlay, (12, 12), (12 + width, 12 + height), (5, 10, 22), -1)
    cv2.addWeighted(overlay, 0.72, frame, 0.28, 0, dst=frame)
    cv2.rectangle(frame, (12, 12), (12 + width, 12 + height), (90, 160, 255), 2)
    y = 46
    for line in lines:
        cv2.putText(
            frame,
            line,
            (30, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.68,
            (245, 248, 255),
            2,
            cv2.LINE_AA,
        )
        y += 24


def draw_control_points(frame: np.ndarray, points: list[CalibrationPoint]) -> None:
    for index, point in enumerate(points, start=1):
        center = (int(round(point.pixel_x)), int(round(point.pixel_y)))
        cv2.circle(frame, center, 8, (0, 220, 255), -1, cv2.LINE_AA)
        cv2.circle(frame, center, 12, (10, 16, 28), 2, cv2.LINE_AA)
        cv2.putText(
            frame,
            f"P{index} ({point.world_x:.1f},{point.world_y:.1f}m)",
            (center[0] + 12, center[1] - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.58,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )


def draw_validation_segments(
    frame: np.ndarray,
    validation_segments: list[dict[str, Any]],
    inverse_homography: np.ndarray,
) -> None:
    for segment in validation_segments:
        pixel_start = segment.get("pixel_start")
        pixel_end = segment.get("pixel_end")
        world_start = segment.get("world_start")
        world_end = segment.get("world_end")
        if (
            not isinstance(pixel_start, list)
            or not isinstance(pixel_end, list)
            or not isinstance(world_start, list)
            or not isinstance(world_end, list)
        ):
            continue
        expected_start = (int(round(float(pixel_start[0]))), int(round(float(pixel_start[1]))))
        expected_end = (int(round(float(pixel_end[0]))), int(round(float(pixel_end[1]))))
        projected_start = world_to_pixel(
            inverse_homography,
            (float(world_start[0]), float(world_start[1])),
        )
        projected_end = world_to_pixel(
            inverse_homography,
            (float(world_end[0]), float(world_end[1])),
        )
        cv2.line(frame, expected_start, expected_end, (60, 230, 120), 4, cv2.LINE_AA)
        draw_dashed_line(frame, projected_start, projected_end, (40, 80, 255), thickness=3)
        label_origin = (expected_start[0] + 8, expected_start[1] - 8)
        cv2.putText(
            frame,
            str(segment.get("name", "validation")),
            label_origin,
            cv2.FONT_HERSHEY_SIMPLEX,
            0.58,
            (240, 255, 240),
            2,
            cv2.LINE_AA,
        )


def draw_grid(frame: np.ndarray, grid: HomographyGrid | None) -> None:
    if grid is None:
        return
    layer = frame.copy()
    for line in grid.lines:
        start = (int(round(line.pixel_start[0])), int(round(line.pixel_start[1])))
        end = (int(round(line.pixel_end[0])), int(round(line.pixel_end[1])))
        draw_dashed_line(layer, start, end, (220, 230, 240), thickness=2)
    cv2.addWeighted(layer, 0.35, frame, 0.65, 0, dst=frame)


def resolve_calibration(
    video_path: Path,
    presets: CalibrationPresetCatalog,
) -> dict[str, Any]:
    metadata = inspect_video(video_path)
    profile = profile_for_clip(video_path, presets.scene_profiles)
    camera_profile = match_camera_profile(video_path, presets.camera_profiles)
    video_preset = presets.video_calibrations.get(video_path.name)
    if video_preset is not None:
        calibration = build_calibration(
            metadata["width"],
            metadata["height"],
            profile,
            video_preset,
        )
        source = "video_manual_preset"
        declared_trusted = video_preset.calibration_trusted
        points = video_preset.points
        road_polygon = video_preset.road_plane_polygon_world
        road_polygon_pixel = video_preset.road_plane_polygon_pixel
        validation_segments = video_preset.validation_segments
        scale_prior = video_preset.scale_prior
        profile_notes = video_preset.profile_notes
        annotation_method = video_preset.annotation_method
        evidence_sources = video_preset.evidence_sources
        world_width_m = profile.world_width_m
        world_length_m = profile.world_length_m
        grid_spacing_m = 5.0
        profile_id = camera_profile.profile_id if camera_profile is not None else profile.name
        profile_payload = asdict(camera_profile) if camera_profile is not None else asdict(profile)
    elif camera_profile is not None:
        calibration = build_camera_profile_calibration(camera_profile)
        source = "camera_manual_preset"
        declared_trusted = camera_profile.calibration_trusted
        points = camera_profile.manual_control_points
        road_polygon = camera_profile.road_plane_polygon_world
        road_polygon_pixel = None
        validation_segments = camera_profile.validation_segments
        scale_prior = (
            {"kind": "camera_profile", "description": camera_profile.scale_prior_used}
            if camera_profile.scale_prior_used
            else None
        )
        profile_notes = camera_profile.display_name
        annotation_method = camera_profile.annotation_method
        evidence_sources = camera_profile.evidence_sources
        world_width_m = camera_profile.world_width_m
        world_length_m = camera_profile.world_length_m
        grid_spacing_m = camera_profile.grid_spacing_m
        profile_id = camera_profile.profile_id
        profile_payload = asdict(camera_profile)
    else:
        calibration = build_calibration(
            metadata["width"],
            metadata["height"],
            profile,
            video_preset,
        )
        source = "scene_profile_preset"
        declared_trusted = False
        points = []
        road_polygon = None
        road_polygon_pixel = None
        validation_segments = []
        scale_prior = None
        profile_notes = profile.notes
        annotation_method = None
        evidence_sources = []
        world_width_m = profile.world_width_m
        world_length_m = profile.world_length_m
        grid_spacing_m = 5.0
        profile_id = profile.name
        profile_payload = asdict(profile)
    validation_error = validation_segment_max_error_px(calibration, validation_segments)
    independent_validation_segment_count = validation_independent_segment_count(
        points,
        validation_segments,
    )
    provenance_issues = manual_calibration_provenance_issues(
        annotation_method=annotation_method,
        evidence_sources=evidence_sources,
        scale_prior=scale_prior,
    )
    trusted = is_trusted_manual_calibration(
        calibration,
        source,
        declared_trusted,
        validation_error,
        independent_validation_segment_count,
        annotation_method,
        evidence_sources,
        scale_prior,
    )
    grid = (
        CalibrationService().build_homography_grid(
            calibration,
            frame_width=metadata["width"],
            frame_height=metadata["height"],
            world_width_m=world_width_m,
            world_length_m=world_length_m,
            spacing_m=grid_spacing_m,
            calibration_source=source,
            calibration_trusted=True,
            road_plane_polygon_world=road_polygon,
            validation_max_error_px=validation_error,
        )
        if trusted
        else None
    )
    return {
        "metadata": metadata,
        "profile_id": profile_id,
        "profile": profile_payload,
        "calibration": calibration,
        "source": source,
        "declared_trusted": declared_trusted,
        "calibration_trusted": trusted,
        "points": points,
        "road_plane_polygon_pixel": road_polygon_pixel,
        "road_plane_polygon_world": road_polygon,
        "scale_prior": scale_prior,
        "profile_notes": profile_notes,
        "annotation_method": annotation_method,
        "evidence_sources": evidence_sources,
        "provenance_trusted": not provenance_issues,
        "provenance_issues": provenance_issues,
        "validation_segments": validation_segments,
        "validation_max_error_px": validation_error,
        "independent_validation_segment_count": independent_validation_segment_count,
        "grid": grid,
    }


def build_clip_qa(
    video_path: Path,
    output_dir: Path,
    presets: CalibrationPresetCatalog,
    frame_index: int,
) -> dict[str, Any]:
    resolved = resolve_calibration(video_path, presets)
    calibration = resolved["calibration"]
    frame = read_video_frame(video_path, frame_index)
    inverse_h = np.linalg.inv(calibration.homography_matrix).astype(np.float64)
    draw_grid(frame, resolved["grid"])
    draw_validation_segments(frame, resolved["validation_segments"], inverse_h)
    draw_control_points(frame, resolved["points"])
    status = "trusted" if resolved["calibration_trusted"] else "needs_manual_refinement"
    draw_text_panel(
        frame,
        [
            f"{video_path.name}",
            f"source={resolved['source']} status={status}",
            (
                f"world_rmse={calibration.pixel_to_world_rmse_m:.3f}m "
                f"pixel_rmse={calibration.world_to_pixel_rmse_px:.2f}px"
            ),
            f"validation_max_error={resolved['validation_max_error_px']}",
            (
                "independent_validation_segments="
                f"{resolved['independent_validation_segment_count']}"
            ),
            "green=expected validation, red dashed=H-projected validation",
        ],
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    image_path = output_dir / f"{video_path.stem}_qa.jpg"
    if not cv2.imwrite(str(image_path), frame):
        raise ValueError(f"could not write QA image: {image_path}")
    return {
        "clip": video_path.name,
        "qa_image": str(image_path),
        "profile_id": resolved["profile_id"],
        "calibration_source": resolved["source"],
        "declared_trusted": resolved["declared_trusted"],
        "calibration_trusted": resolved["calibration_trusted"],
        "annotation_method": resolved["annotation_method"],
        "evidence_sources": resolved["evidence_sources"],
        "provenance_trusted": resolved["provenance_trusted"],
        "provenance_issues": resolved["provenance_issues"],
        "calibration_quality": calibration.calibration_quality,
        "pixel_to_world_rmse_m": calibration.pixel_to_world_rmse_m,
        "world_to_pixel_rmse_px": calibration.world_to_pixel_rmse_px,
        "validation_max_error_px": resolved["validation_max_error_px"],
        "independent_validation_segment_count": resolved[
            "independent_validation_segment_count"
        ],
        "point_count": len(resolved["points"]),
        "validation_segment_count": len(resolved["validation_segments"]),
        "has_scale_prior": bool(resolved["scale_prior"]),
        "has_profile_notes": bool(resolved["profile_notes"]),
        "has_road_plane_polygon_pixel": bool(resolved["road_plane_polygon_pixel"]),
        "has_road_plane_polygon_world": bool(resolved["road_plane_polygon_world"]),
        "grid_rendered": resolved["grid"] is not None,
    }


def render_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Calibration QA Summary",
        "",
        f"- Output dir: `{summary['output_dir']}`",
        f"- Trusted clips: `{summary['trusted_count']}/{summary['clip_count']}`",
        "",
        (
            "| Clip | Source | Trusted | Pixel RMSE | Validation Max | "
            "Independent Segments | Grid | QA |"
        ),
        "| --- | --- | --- | ---: | ---: | ---: | --- | --- |",
    ]
    for row in summary["clips"]:
        validation = row["validation_max_error_px"]
        lines.append(
            "| "
            + " | ".join(
                [
                    row["clip"],
                    row["calibration_source"],
                    str(row["calibration_trusted"]),
                    f"{row['world_to_pixel_rmse_px']:.2f}px",
                    "N/A" if validation is None else f"{validation:.2f}px",
                    str(row["independent_validation_segment_count"]),
                    str(row["grid_rendered"]),
                    Path(row["qa_image"]).name,
                ],
            )
            + " |",
        )
    lines.extend(
        [
            "",
            "## Gate",
            "",
            "- `validation_max_error_px < 8`: ideal",
            "- `validation_max_error_px < 15`: usable",
            "- otherwise: grid must stay suppressed",
        ],
    )
    return "\n".join(lines) + "\n"


def build_qa_summary(
    input_dir: Path,
    output_dir: Path,
    calibration_presets: Path,
    camera_profiles: Path,
    clips: list[str],
    frame_index: int,
) -> dict[str, Any]:
    presets = load_calibration_presets(calibration_presets)
    presets = CalibrationPresetCatalog(
        scene_profiles=presets.scene_profiles,
        video_calibrations=presets.video_calibrations,
        camera_profiles=load_camera_profiles(camera_profiles),
    )
    clip_rows = [
        build_clip_qa(input_dir / clip, output_dir, presets, frame_index)
        for clip in clips
    ]
    summary = {
        "output_dir": str(output_dir),
        "clip_count": len(clip_rows),
        "trusted_count": sum(1 for row in clip_rows if row["calibration_trusted"]),
        "clips": clip_rows,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "calibration_qa_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
    )
    (output_dir / "calibration_qa_summary.md").write_text(render_markdown(summary))
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build visual QA assets for homography calibration.",
    )
    parser.add_argument("--input-dir", default="data/tests/real_video_clips")
    parser.add_argument("--output-dir", default="data/outputs/calibration_qa")
    parser.add_argument("--calibration-presets", default="data/tests/calibration_presets.yaml")
    parser.add_argument("--camera-profiles", default="data/tests/camera_profiles.yaml")
    parser.add_argument("--clips", nargs="*", default=GOLDEN_CLIPS)
    parser.add_argument("--frame-index", type=int, default=1)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = build_qa_summary(
        input_dir=Path(args.input_dir),
        output_dir=Path(args.output_dir),
        calibration_presets=Path(args.calibration_presets),
        camera_profiles=Path(args.camera_profiles),
        clips=args.clips,
        frame_index=args.frame_index,
    )
    print(
        json.dumps(
            {
                "clip_count": summary["clip_count"],
                "trusted_count": summary["trusted_count"],
                "output_dir": summary["output_dir"],
            },
            ensure_ascii=False,
            indent=2,
        ),
    )


if __name__ == "__main__":
    main()
