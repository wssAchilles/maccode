from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLBACKEND", "Agg")

from domain.speed.geometry_diagnostics import (
    TrackGeometryDiagnostic,
    TrackGeometryDiagnosticBuilder,
    reports_from_analysis_payload,
)


def load_payload(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_speed_plot(diagnostic: TrackGeometryDiagnostic, path: Path) -> None:
    import matplotlib.pyplot as plt

    timestamps = [
        float(row["timestamp_sec"])
        for row in diagnostic.rows
        if row.get("timestamp_sec") is not None
    ]
    speeds = [
        row.get("filtered_speed_kmh")
        for row in diagnostic.rows
        if row.get("timestamp_sec") is not None
    ]
    if not timestamps:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fig, axis = plt.subplots(figsize=(8, 4))
    axis.plot(timestamps, speeds, marker="o", linewidth=1.5)
    axis.set_xlabel("time (s)")
    axis.set_ylabel("speed (km/h)")
    axis.set_title(f"track {diagnostic.tracker_id} speed")
    axis.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def write_world_path_plot(diagnostic: TrackGeometryDiagnostic, path: Path) -> None:
    import matplotlib.pyplot as plt

    points = [
        (float(row["world_x"]), float(row["world_y"]))
        for row in diagnostic.rows
        if row.get("world_x") is not None and row.get("world_y") is not None
    ]
    if not points:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fig, axis = plt.subplots(figsize=(5, 5))
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    axis.plot(xs, ys, marker="o", linewidth=1.5)
    axis.set_xlabel("world x (m)")
    axis.set_ylabel("world y (m)")
    axis.set_title(f"track {diagnostic.tracker_id} world path")
    axis.axis("equal")
    axis.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def write_plane_grid_overlay(
    payload: dict[str, Any],
    reports: list[dict[str, Any]],
    path: Path,
) -> None:
    import matplotlib.pyplot as plt

    grid = payload.get("homography_grid")
    if not isinstance(grid, dict):
        for report in reports:
            candidate = report.get("homography_grid")
            if isinstance(candidate, dict):
                grid = candidate
                break
    if not isinstance(grid, dict):
        return
    lines = grid.get("lines")
    if not isinstance(lines, list) or not lines:
        return
    width = float(grid.get("frame_width") or 100)
    height = float(grid.get("frame_height") or 100)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig, axis = plt.subplots(figsize=(8, 5))
    for line in lines:
        if not isinstance(line, dict):
            continue
        start = line.get("pixel_start")
        end = line.get("pixel_end")
        if not (
            isinstance(start, list)
            and isinstance(end, list)
            and len(start) == 2
            and len(end) == 2
        ):
            continue
        axis.plot(
            [float(start[0]), float(end[0])],
            [float(start[1]), float(end[1])],
            linewidth=0.8,
        )
    axis.set_xlim(0, width)
    axis.set_ylim(height, 0)
    axis.set_xlabel("pixel x")
    axis.set_ylabel("pixel y")
    axis.set_title("metric plane BEV grid overlay")
    axis.grid(False)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export per-frame geometry diagnostics for one tracked object.",
    )
    parser.add_argument("--analysis-json", required=True, type=Path)
    parser.add_argument("--tracker-id", required=True, type=int)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    payload = load_payload(args.analysis_json)
    reports = reports_from_analysis_payload(payload)
    diagnostic = TrackGeometryDiagnosticBuilder().build(
        reports,
        tracker_id=args.tracker_id,
    )
    prefix = f"track_{args.tracker_id}"
    diagnostic.write_csv(args.output_dir / f"{prefix}_geometry.csv")
    diagnostic.write_json(args.output_dir / f"{prefix}_geometry.json")
    write_speed_plot(diagnostic, args.output_dir / f"{prefix}_speed_plot.png")
    write_world_path_plot(diagnostic, args.output_dir / f"{prefix}_world_path.png")
    write_plane_grid_overlay(payload, reports, args.output_dir / "plane_grid_overlay.png")


if __name__ == "__main__":
    main()
