from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.import_golden_calibration_picks import calibration_pick_keys, load_payload

PROFILE_METADATA_KEY = "__profile_metadata__"


def merge_pick_payloads(paths: list[Path]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    merged_metadata: dict[str, Any] = {}
    duplicate_clips: list[str] = []

    for path in paths:
        payload = load_payload(path)
        metadata = payload.get(PROFILE_METADATA_KEY)
        if isinstance(metadata, dict):
            for clip, profile in metadata.items():
                if clip in merged_metadata:
                    duplicate_clips.append(f"{clip} metadata from {path}")
                merged_metadata[clip] = profile
        for clip in calibration_pick_keys(payload):
            if clip in merged:
                duplicate_clips.append(f"{clip} picks from {path}")
            merged[clip] = payload[clip]

    if duplicate_clips:
        joined = "; ".join(duplicate_clips)
        raise ValueError(f"duplicate clip entries are not allowed: {joined}")
    if merged_metadata:
        merged[PROFILE_METADATA_KEY] = merged_metadata
    return merged


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Merge per-clip calibration picker JSON files into one "
            "golden-calibration-picks.json for preflight/import."
        ),
    )
    parser.add_argument("inputs", nargs="+", help="Per-clip picker JSON files.")
    parser.add_argument(
        "--output",
        default="data/outputs/golden_calibration_packet/golden-calibration-picks.json",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = merge_pick_payloads([Path(path) for path in args.inputs])
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "input_count": len(args.inputs),
                "clip_count": len(calibration_pick_keys(payload)),
                "has_profile_metadata": PROFILE_METADATA_KEY in payload,
                "output": str(output),
            },
            ensure_ascii=False,
            indent=2,
        ),
    )


if __name__ == "__main__":
    main()
