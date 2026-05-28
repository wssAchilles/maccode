from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.validate_calibration_presets import render_markdown, validate_catalog


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _extract_video_calibrations(payload: dict[str, Any]) -> dict[str, Any]:
    if "video_calibrations" in payload:
        calibrations = payload["video_calibrations"]
    else:
        calibrations = payload
    if not isinstance(calibrations, dict) or not calibrations:
        raise ValueError("input must contain a non-empty video_calibrations object")
    return calibrations


def merge_preset(
    base_path: Path,
    input_path: Path,
    output_path: Path,
    *,
    overwrite: bool,
    required_clips: list[str] | None = None,
) -> dict[str, Any]:
    base = load_json(base_path)
    incoming = _extract_video_calibrations(load_json(input_path))
    current = dict(base.get("video_calibrations", {}))
    duplicate_clips = sorted(set(current) & set(incoming))
    if duplicate_clips and not overwrite:
        raise ValueError(
            "refusing to overwrite existing video calibrations: "
            + ", ".join(duplicate_clips),
        )
    base["video_calibrations"] = {**current, **incoming}
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(base, ensure_ascii=False, indent=2))

    validation = validate_catalog(output_path, required_clips=required_clips)
    (output_path.parent / "merged_calibration_validation.json").write_text(
        json.dumps(validation, ensure_ascii=False, indent=2),
    )
    (output_path.parent / "merged_calibration_validation.md").write_text(
        render_markdown(validation),
    )
    return {
        "output_path": str(output_path),
        "merged_clips": sorted(incoming),
        "duplicate_clips": duplicate_clips,
        "validation": validation,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Merge frontend-exported video calibration entries into a preset file.",
    )
    parser.add_argument("--base", default="data/tests/calibration_presets.json")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", default="data/tests/calibration_presets.merged.json")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--required-clips", nargs="*", default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = merge_preset(
        base_path=Path(args.base),
        input_path=Path(args.input),
        output_path=Path(args.output),
        overwrite=args.overwrite,
        required_clips=args.required_clips,
    )
    validation = summary["validation"]
    print(
        json.dumps(
            {
                "output_path": summary["output_path"],
                "merged_clips": summary["merged_clips"],
                "industrial_readiness": validation["industrial_readiness"],
                "missing_required_clips": validation["missing_required_clips"],
                "readiness_issues": validation["readiness_issues"],
            },
            ensure_ascii=False,
            indent=2,
        ),
    )


if __name__ == "__main__":
    main()
