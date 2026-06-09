from __future__ import annotations

import argparse
import csv
import glob
import hashlib
from pathlib import Path


def user_bucket(user_id: str, buckets: int = 10_000) -> int:
    digest = hashlib.sha256(user_id.encode("utf-8")).hexdigest()
    return int(digest[:12], 16) % buckets


def keep_user(user_id: str, percent: float) -> bool:
    threshold = max(0, min(10_000, int(percent * 100)))
    return user_bucket(user_id or "unknown") < threshold


def write_user_sample(input_paths: list[Path], output_path: Path, percent: float) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    fieldnames: list[str] | None = None
    with output_path.open("w", encoding="utf-8", newline="") as target:
        writer: csv.DictWriter[str] | None = None
        for input_path in input_paths:
            with input_path.open("r", encoding="utf-8", newline="") as source:
                reader = csv.DictReader(source)
                if fieldnames is None:
                    fieldnames = list(reader.fieldnames or [])
                    writer = csv.DictWriter(target, fieldnames=fieldnames)
                    writer.writeheader()
                if writer is None:
                    raise RuntimeError("CSV header is missing")
                for row in reader:
                    if keep_user(str(row.get("user_id") or ""), percent):
                        writer.writerow(row)
                        written += 1
    return written


def expand_inputs(patterns: list[str]) -> list[Path]:
    paths: list[Path] = []
    for pattern in patterns:
        matched = [Path(path) for path in sorted(glob.glob(pattern))] if any(char in pattern for char in "*?[]") else [Path(pattern)]
        paths.extend(path for path in matched if path.is_file())
    if not paths:
        raise FileNotFoundError("no input CSV files matched")
    return paths


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create deterministic user-level CSV samples for Spark/YARN experiments.")
    parser.add_argument("--input", nargs="+", required=True, help="Input CSV path or glob.")
    parser.add_argument("--output", required=True, help="Output CSV path.")
    parser.add_argument("--percent", type=float, required=True, help="User sample percent, for example 1 or 5.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    written = write_user_sample(expand_inputs(args.input), Path(args.output), args.percent)
    print(f"Wrote {written} rows to {args.output} using a deterministic {args.percent:g}% user sample")


if __name__ == "__main__":
    main()
