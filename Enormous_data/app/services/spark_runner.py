from __future__ import annotations

import subprocess
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

from spark_jobs.writers import write_json_atomic


class SparkJobRunningError(RuntimeError):
    pass


class SparkRunner:
    def __init__(self, project_root: str | Path, config_path: str | Path, cache_dir: str | Path):
        self.project_root = Path(project_root)
        self.config_path = Path(config_path)
        self.cache_dir = Path(cache_dir)
        self.lock_path = self.cache_dir / ".refresh.lock"
        self.job_path = self.cache_dir / "job.json"

    def start_refresh(self) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        if self.lock_path.exists():
            raise SparkJobRunningError("spark refresh job is already running")

        self.lock_path.write_text(str(datetime.now(timezone.utc).timestamp()), encoding="utf-8")
        self._write_job("running", "spark refresh started")

        thread = threading.Thread(target=self._run, daemon=True)
        thread.start()

    def _run(self) -> None:
        started_at = datetime.now(timezone.utc).isoformat()
        try:
            result = subprocess.run(
                [sys.executable, "-m", "spark_jobs.main", "--config", str(self.config_path)],
                cwd=self.project_root,
                text=True,
                capture_output=True,
                check=False,
            )
            if result.returncode != 0:
                self._write_job("failed", result.stderr.strip() or "spark refresh failed", started_at=started_at)
                return
            self._write_job("success", result.stdout.strip(), started_at=started_at)
        finally:
            self.lock_path.unlink(missing_ok=True)

    def _write_job(self, status: str, message: str, started_at: str | None = None) -> None:
        now = datetime.now(timezone.utc).isoformat()
        write_json_atomic(
            self.job_path,
            {
                "status": status,
                "started_at": started_at or now,
                "finished_at": None if status == "running" else now,
                "message": message,
            },
        )
