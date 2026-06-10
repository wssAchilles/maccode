from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MANIFEST_LINE_RE = re.compile(r"Spark run manifest:\s*(?P<path>.+)")
MAX_LOG_TAIL_CHARS = 12000


@dataclass(frozen=True)
class PipelineResult:
    returncode: int
    elapsed_seconds: float
    stdout: str
    stderr: str
    manifest_path: str | None = None
    manifest: dict[str, Any] | None = None
    stdout_path: str | None = None
    stderr_path: str | None = None

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
        stdout_path, stderr_path = self._log_paths(run_id)
        with stdout_path.open("w", encoding="utf-8") as stdout_handle, stderr_path.open(
            "w", encoding="utf-8"
        ) as stderr_handle:
            result = subprocess.run(
                command,
                cwd=self.project_root,
                env=self._env(),
                text=True,
                stdout=stdout_handle,
                stderr=stderr_handle,
                check=False,
            )
        stdout = self._tail_text(stdout_path).strip()
        stderr = self._tail_text(stderr_path).strip()
        manifest_path, manifest = self._load_manifest(stdout)
        return PipelineResult(
            returncode=result.returncode,
            elapsed_seconds=round(time.perf_counter() - started, 3),
            stdout=stdout,
            stderr=stderr,
            manifest_path=manifest_path,
            manifest=manifest,
            stdout_path=str(stdout_path),
            stderr_path=str(stderr_path),
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

    @staticmethod
    def _env() -> dict[str, str]:
        env = os.environ.copy()
        env.setdefault("PYSPARK_PYTHON", sys.executable)
        env.setdefault("PYSPARK_DRIVER_PYTHON", sys.executable)
        return env

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

    def _log_paths(self, run_id: str | None) -> tuple[Path, Path]:
        log_dir = Path(os.getenv("SPARK_RUNNER_LOG_DIR", self.project_root / "data" / "cache" / "run_logs"))
        if not log_dir.is_absolute():
            log_dir = self.project_root / log_dir
        log_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        safe_run_id = re.sub(r"[^A-Za-z0-9_.-]+", "-", run_id or "spark-run")
        base = f"{stamp}-{safe_run_id}"
        return log_dir / f"{base}.stdout.log", log_dir / f"{base}.stderr.log"

    @staticmethod
    def _tail_text(path: Path, max_chars: int = MAX_LOG_TAIL_CHARS) -> str:
        if not path.exists():
            return ""
        with path.open("rb") as handle:
            handle.seek(0, os.SEEK_END)
            size = handle.tell()
            handle.seek(max(0, size - max_chars))
            return handle.read().decode("utf-8", errors="replace")
