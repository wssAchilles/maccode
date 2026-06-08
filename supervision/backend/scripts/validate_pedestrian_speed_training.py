from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate pedestrian speed training outputs against acceptance gates.",
    )
    parser.add_argument(
        "--summary",
        default="data/outputs/pedestrian_speed_training/benchmark_summary.json",
    )
    parser.add_argument("--train-coverage-min", type=float, default=0.998)
    parser.add_argument("--validation-coverage-min", type=float, default=0.995)
    parser.add_argument("--max-person-speed-kmh", type=float, default=18.0)
    parser.add_argument("--clip-033-coverage-min", type=float, default=1.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary_path = Path(args.summary)
    payload = json.loads(summary_path.read_text())
    failures = validate_summary(
        payload,
        train_coverage_min=args.train_coverage_min,
        validation_coverage_min=args.validation_coverage_min,
        max_person_speed_kmh=args.max_person_speed_kmh,
        clip_033_coverage_min=args.clip_033_coverage_min,
    )
    result = {
        "summary": str(summary_path),
        "status": "failed" if failures else "passed",
        "failures": failures,
    }
    print(json.dumps(result, indent=2))
    if failures:
        raise SystemExit(1)


def validate_summary(
    payload: dict[str, Any],
    *,
    train_coverage_min: float,
    validation_coverage_min: float,
    max_person_speed_kmh: float,
    clip_033_coverage_min: float,
) -> list[str]:
    failures: list[str] = []
    aggregate = payload.get("aggregate", {})
    if isinstance(aggregate, dict):
        _require_coverage(
            failures,
            aggregate.get("train"),
            "train",
            train_coverage_min,
        )
        _require_coverage(
            failures,
            aggregate.get("validation"),
            "validation",
            validation_coverage_min,
        )
    by_clip = payload.get("by_clip", {})
    if isinstance(by_clip, dict):
        for clip_name, clip_summary in by_clip.items():
            if not isinstance(clip_summary, dict):
                continue
            max_speed = _optional_float(clip_summary.get("max_pedestrian_speed_kmh"))
            if max_speed is not None and max_speed > max_person_speed_kmh:
                failures.append(
                    f"{clip_name} max speed {max_speed:.3f} exceeds {max_person_speed_kmh:.3f}",
                )
            if clip_name.startswith("033_"):
                coverage = _optional_float(clip_summary.get("person_speed_coverage"))
                if coverage is None or coverage < clip_033_coverage_min:
                    failures.append(
                        f"{clip_name} coverage {coverage} below {clip_033_coverage_min:.3f}",
                    )
    return failures


def _require_coverage(
    failures: list[str],
    summary: object,
    label: str,
    minimum: float,
) -> None:
    if not isinstance(summary, dict):
        failures.append(f"{label} summary missing")
        return
    coverage = _optional_float(summary.get("person_speed_coverage"))
    if coverage is None or coverage < minimum:
        failures.append(f"{label} coverage {coverage} below {minimum:.3f}")


def _optional_float(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


if __name__ == "__main__":
    sys.exit(main())
