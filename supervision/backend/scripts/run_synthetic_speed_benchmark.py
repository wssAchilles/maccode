from __future__ import annotations

import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from domain.speed.synthetic_benchmark import run_default_synthetic_speed_benchmark


def main() -> None:
    results = [
        result.to_dict()
        for result in run_default_synthetic_speed_benchmark()
    ]
    print(json.dumps({"scenarios": results}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
