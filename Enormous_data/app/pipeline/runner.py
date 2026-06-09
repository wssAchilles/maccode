from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


MANIFEST_LINE_RE = re.compile(r"Spark run manifest:\s*(?P<path>.+)")


@dataclass(frozen=True)
class PipelineResult:
    returncode: int
    elapsed_seconds: float
    stdout: str
    stderr: str
    manifest_path: str | None = None
    manifest: dict[str, Any] | None = None

    @property
    def succeeded(self) -> bool:
        return self.returncode == 0


class SparkPipelineRunner:
    def __init__(self, project_root: str | Path, submit_script: str | Path | None = None):
        self.project_root = Path(project_root)
        script = submit_script or os.getenv("SPARK_SUBMIT_SCRIPT")
        self.submit_script = Path(script) if script else None

    def run(self, config_path: str | Path, run_id: str | None = None) -> PipelineResult:
        started = time.perf_counter()
        command = self._command(config_path, run_id)
        result = subprocess.run(
            command,
            cwd=self.project_root,
            text=True,
            capture_output=True,
            check=False,
        )
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        manifest_path, manifest = self._load_manifest(stdout)
        return PipelineResult(
            returncode=result.returncode,
            elapsed_seconds=round(time.perf_counter() - started, 3),
            stdout=stdout,
            stderr=stderr,
            manifest_path=manifest_path,
            manifest=manifest,
        )

    def _command(self, config_path: str | Path, run_id: str | None) -> list[str]:
        if self.submit_script:
            command = [str(self.submit_script), str(config_path)]
            if run_id:
                command.append(run_id)
            return command

        command = [sys.executable, "-m", "spark_jobs.main", "--config", str(config_path)]
        if run_id:
            command.extend(["--run-id", run_id])
        return command

    def _load_manifest(self, stdout: str) -> tuple[str | None, dict[str, Any] | None]:
        manifest_path = self._find_manifest_path(stdout)
        if not manifest_path:
            return None, None
        path = Path(manifest_path)
        if not path.is_absolute():
            path = self.project_root / path
        if not path.exists():
            return manifest_path, None
        with path.open("r", encoding="utf-8") as handle:
            return manifest_path, json.load(handle)

    @staticmethod
    def _find_manifest_path(stdout: str) -> str | None:
        for line in stdout.splitlines():
            match = MANIFEST_LINE_RE.search(line)
            if match:
                return match.group("path").strip()
        return None
