from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/mpl")

import cv2

from scripts.analyze_real_videos import default_profile_for_clip, inspect_video


def build_template_points(
    width: int,
    height: int,
    world_width_m: float,
    world_length_m: float,
) -> list[dict[str, float]]:
    return [
        {
            "pixel_x": round(0.20 * width, 2),
            "pixel_y": round(0.92 * height, 2),
            "world_x": 0.0,
            "world_y": 0.0,
        },
        {
            "pixel_x": round(0.86 * width, 2),
            "pixel_y": round(0.92 * height, 2),
            "world_x": world_width_m,
            "world_y": 0.0,
        },
        {
            "pixel_x": round(0.62 * width, 2),
            "pixel_y": round(0.44 * height, 2),
            "world_x": world_width_m,
            "world_y": world_length_m,
        },
        {
            "pixel_x": round(0.38 * width, 2),
            "pixel_y": round(0.44 * height, 2),
            "world_x": 0.0,
            "world_y": world_length_m,
        },
    ]


def build_video_calibration_template(video_path: Path) -> dict[str, Any]:
    metadata = inspect_video(video_path)
    profile = default_profile_for_clip(video_path)
    return {
        "notes": (
            "Replace pixel_x/pixel_y with manually clicked ground-control points "
            "from the exported calibration frame before claiming calibrated speed."
        ),
        "frame_reference": f"calibration_frames/{video_path.stem}.jpg",
        "profile_name": profile.name,
        "video_width": metadata["width"],
        "video_height": metadata["height"],
        "fps": metadata["fps"],
        "position_rmse_floor_m": profile.position_rmse_floor_m,
        "calibration_scale_uncertainty_pct": profile.calibration_scale_uncertainty_pct,
        "points": build_template_points(
            metadata["width"],
            metadata["height"],
            profile.world_width_m,
            profile.world_length_m,
        ),
    }


def export_calibration_frame(video_path: Path, output_path: Path, frame_index: int = 1) -> None:
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise ValueError(f"could not open video: {video_path}")
    try:
        capture.set(cv2.CAP_PROP_POS_FRAMES, max(frame_index - 1, 0))
        ok, frame = capture.read()
        if not ok:
            raise ValueError(f"could not read frame {frame_index} from video: {video_path}")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if not cv2.imwrite(str(output_path), frame):
            raise ValueError(f"could not write calibration frame: {output_path}")
    finally:
        capture.release()


def prepare_assets(
    input_dir: Path,
    output_dir: Path,
    limit: int,
    frame_index: int,
) -> dict[str, Any]:
    clips = sorted(input_dir.glob("*.mp4"))
    if limit > 0:
        clips = clips[:limit]
    output_dir.mkdir(parents=True, exist_ok=True)
    frame_dir = output_dir / "calibration_frames"
    templates: dict[str, Any] = {}
    for video_path in clips:
        export_calibration_frame(
            video_path,
            frame_dir / f"{video_path.stem}.jpg",
            frame_index=frame_index,
        )
        templates[video_path.name] = build_video_calibration_template(video_path)
    payload = {
        "schema_version": 1,
        "notes": (
            "Copy entries into data/tests/calibration_presets.json video_calibrations "
            "after replacing template pixel coordinates with manually surveyed points."
        ),
        "video_calibrations": templates,
    }
    (output_dir / "video_calibration_templates.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
    )
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export calibration frames and per-video calibration templates.",
    )
    parser.add_argument("--input-dir", default="data/tests/real_video_clips")
    parser.add_argument("--output-dir", default="data/outputs/calibration_assets")
    parser.add_argument("--limit", type=int, default=4)
    parser.add_argument("--frame-index", type=int, default=1)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = prepare_assets(
        input_dir=Path(args.input_dir),
        output_dir=Path(args.output_dir),
        limit=args.limit,
        frame_index=args.frame_index,
    )
    print(
        json.dumps(
            {
                "generated_templates": len(payload["video_calibrations"]),
                "output_dir": args.output_dir,
            },
            ensure_ascii=False,
            indent=2,
        ),
    )


if __name__ == "__main__":
    main()
