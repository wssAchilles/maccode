from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_json_atomic(path: str | Path, payload: Any) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temp_path = target.with_suffix(target.suffix + ".tmp")
    temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temp_path.replace(target)


def write_metric_files(output_dir: str | Path, metrics: dict[str, object]) -> None:
    base = Path(output_dir)
    base.mkdir(parents=True, exist_ok=True)
    for name, payload in metrics.items():
        write_json_atomic(base / f"{name}.json", payload)
