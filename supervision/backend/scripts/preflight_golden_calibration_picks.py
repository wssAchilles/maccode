from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from application.services.calibration_preset_store import CalibrationPresetStore

from scripts.build_calibration_qa import GOLDEN_CLIPS
from scripts.import_golden_calibration_picks import build_entry, load_payload, metadata_from_picks


def preflight_picks(
    *,
    picks_path: Path,
    profile_metadata_path: Path | None,
    clips: list[str],
) -> dict[str, Any]:
    file_issues: list[str] = []
    if picks_path.exists():
        picks = load_payload(picks_path)
    else:
        picks = {}
        file_issues.append(f"missing picks file: {picks_path}")
    if profile_metadata_path is None:
        profiles = metadata_from_picks(picks)
        if not profiles:
            file_issues.append("missing embedded profile metadata: __profile_metadata__")
    elif profile_metadata_path.exists():
        profiles = load_payload(profile_metadata_path)
    else:
        profiles = {}
        file_issues.append(f"missing profile metadata file: {profile_metadata_path}")
    store = CalibrationPresetStore()
    rows: list[dict[str, Any]] = []
    for clip in clips:
        issues: list[str] = []
        diagnostics: dict[str, Any] | None = None
        entry: dict[str, Any] | None = None
        if clip not in picks:
            issues.append("missing picks")
        if clip not in profiles:
            issues.append("missing profile metadata")
        if not issues:
            try:
                entry = build_entry(clip, picks[clip], profiles[clip], trusted=True)
                diagnostics = store.validate_entry(entry)
            except Exception as exc:  # noqa: BLE001
                issues.append(str(exc))
        if diagnostics is not None and diagnostics["calibration_trusted"] is not True:
            issues.append("validation gate did not mark calibration trusted")
        if diagnostics is not None and diagnostics.get("provenance_trusted") is False:
            issues.extend(
                str(issue) for issue in diagnostics.get("provenance_issues", [])
            )
        row = {
            "clip": clip,
            "preflight_ready": not issues and diagnostics is not None,
            "issues": issues,
            "point_count": len(entry["points"]) if entry else 0,
            "validation_segment_count": (
                len(entry["validation_segments"]) if entry else 0
            ),
            "has_road_plane_polygon_pixel": bool(
                entry and entry.get("road_plane_polygon_pixel"),
            ),
            "has_scale_prior": bool(entry and entry.get("scale_prior")),
            "has_profile_notes": bool(entry and entry.get("profile_notes")),
            "calibration_trusted": (
                diagnostics.get("calibration_trusted") if diagnostics else False
            ),
            "world_to_pixel_rmse_px": (
                diagnostics.get("world_to_pixel_rmse_px") if diagnostics else None
            ),
            "validation_max_error_px": (
                diagnostics.get("validation_max_error_px") if diagnostics else None
            ),
            "independent_validation_segment_count": (
                diagnostics.get("independent_validation_segment_count")
                if diagnostics
                else 0
            ),
            "provenance_trusted": (
                diagnostics.get("provenance_trusted") if diagnostics else False
            ),
            "provenance_issues": (
                diagnostics.get("provenance_issues", []) if diagnostics else []
            ),
        }
        rows.append(row)
    return {
        "picks_path": str(picks_path),
        "profile_metadata_path": str(profile_metadata_path)
        if profile_metadata_path is not None
        else "embedded:__profile_metadata__",
        "file_issues": file_issues,
        "clip_count": len(rows),
        "ready_count": sum(1 for row in rows if row["preflight_ready"]),
        "all_ready": not file_issues and all(row["preflight_ready"] for row in rows),
        "clips": rows,
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Golden Calibration Picks Preflight",
        "",
        f"- Picks: `{payload['picks_path']}`",
        f"- Profile metadata: `{payload['profile_metadata_path']}`",
        f"- Ready clips: `{payload['ready_count']}/{payload['clip_count']}`",
        f"- All ready: `{payload['all_ready']}`",
        "",
        (
            "| Clip | Ready | Points | Segments | Independent | "
            "Validation | Trusted | Issues |"
        ),
        "| --- | --- | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    if payload.get("file_issues"):
        lines.extend(["## File Issues", ""])
        lines.extend(f"- {issue}" for issue in payload["file_issues"])
        lines.append("")
    for row in payload["clips"]:
        validation = row["validation_max_error_px"]
        lines.append(
            "| "
            + " | ".join(
                [
                    row["clip"],
                    str(row["preflight_ready"]),
                    str(row["point_count"]),
                    str(row["validation_segment_count"]),
                    str(row["independent_validation_segment_count"]),
                    "N/A" if validation is None else f"{float(validation):.2f}px",
                    str(row["calibration_trusted"]),
                    "<br>".join(row["issues"]) if row["issues"] else "none",
                ],
            )
            + " |",
        )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Preflight golden calibration picker output without writing YAML. "
            "Use before import_golden_calibration_picks.py --trusted."
        ),
    )
    parser.add_argument(
        "--picks",
        default="data/outputs/golden_calibration_packet/golden-calibration-picks.json",
    )
    parser.add_argument(
        "--profile-metadata",
        default=None,
        help=(
            "Optional YAML/JSON profile metadata. If omitted, reads "
            "__profile_metadata__ from the picker JSON."
        ),
    )
    parser.add_argument("--output-dir", default="data/outputs/golden_calibration_preflight")
    parser.add_argument("--clips", nargs="*", default=GOLDEN_CLIPS)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with status 1 unless every requested clip passes preflight.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = preflight_picks(
        picks_path=Path(args.picks),
        profile_metadata_path=Path(args.profile_metadata)
        if args.profile_metadata
        else None,
        clips=list(args.clips),
    )
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "golden_calibration_preflight.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "golden_calibration_preflight.md").write_text(
        render_markdown(payload),
        encoding="utf-8",
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if args.strict and not payload["all_ready"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
