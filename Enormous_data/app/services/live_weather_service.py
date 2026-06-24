from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.services.metric_cache import CacheNotReadyError
from app.services.open_meteo import OpenMeteoClient, fetch_current_with_cache, fetch_historical_with_cache, fetch_hourly_forecast_with_cache
from app.services.spark_runner import SparkJobRunningError
from spark_jobs.main import load_config, resolve_input_path
from spark_jobs.writers import write_json_atomic


LIVE_JOB_ACTIVE_STATUSES = {"queued", "running"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class LiveWeatherService:
    def __init__(
        self,
        *,
        project_root: str | Path,
        config_path: str | Path,
        cache_dir: str | Path,
        live_dir: str | Path | None = None,
    ):
        self.project_root = Path(project_root)
        self.config_path = Path(config_path)
        self.cache_dir = Path(cache_dir)
        self.live_dir = Path(live_dir) if live_dir else self.project_root / "data" / "live"
        self.status_path = self.cache_dir / "live_training_status.json"
        self.current_weather_path = self.live_dir / "current_weather.json"
        self.forecast_weather_path = self.live_dir / "forecast_weather_24h.json"
        self.weather_history_path = self.live_dir / "weather_history_2019.csv"

    def enqueue_refresh(self) -> dict[str, Any]:
        current = self.load_status(default_none=True)
        if current and current.get("status") in LIVE_JOB_ACTIVE_STATUSES:
            raise SparkJobRunningError(f"live weather training already {current['status']}: {current.get('run_id')}")
        run_id = uuid4().hex
        status = {
            "run_id": run_id,
            "job_type": "live_weather_training",
            "status": "queued",
            "created_at": utc_now(),
            "started_at": None,
            "finished_at": None,
            "elapsed_seconds": None,
            "message": "live weather training queued",
            "quality_status": "pending",
        }
        write_json_atomic(self.status_path, status)
        thread = threading.Thread(target=self._run, args=(run_id,), daemon=True)
        thread.start()
        return status

    def load_status(self, default_none: bool = False) -> dict[str, Any] | None:
        if not self.status_path.exists():
            if default_none:
                return None
            raise CacheNotReadyError("live training status cache not found: live_training_status.json")
        with self.status_path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _run(self, run_id: str) -> None:
        started = time.perf_counter()
        started_at = utc_now()
        self._write_status(run_id, status="running", started_at=started_at, message="fetching Open-Meteo weather data")
        try:
            config = load_config(self._config_path())
            input_path = resolve_input_path(config)
            start_date, end_date = infer_date_range(self.project_root / input_path if not str(input_path).startswith("hdfs://") else input_path)
            live_config = config.get("live_weather", {})
            client = OpenMeteoClient(
                city=str(live_config.get("city", "上海")),
                latitude=float(live_config.get("latitude", 31.2304)),
                longitude=float(live_config.get("longitude", 121.4737)),
                timezone_name=str(live_config.get("timezone", "Asia/Shanghai")),
            )
            self.live_dir.mkdir(parents=True, exist_ok=True)
            historical = fetch_historical_with_cache(
                self.weather_history_path,
                start_date=start_date,
                end_date=end_date,
                client=client,
                force=False,
            )
            current = fetch_current_with_cache(self.current_weather_path, client=client, force=True)
            forecast = fetch_hourly_forecast_with_cache(
                self.forecast_weather_path,
                client=client,
                force=True,
                horizon_hours=int(live_config.get("forecast_horizon_hours", 24)),
            )
            self._write_status(
                run_id,
                status="running",
                started_at=started_at,
                message="running Spark live weather micro-batch",
                weather_history=historical,
                current_weather_source_status=current.get("source_status"),
                forecast_weather_source_status=forecast.get("source_status"),
            )
            result = self._run_spark(run_id)
            elapsed = round(time.perf_counter() - started, 3)
            status_payload = self._load_generated_status(run_id)
            status_payload.update(
                {
                    "status": "succeeded" if result.returncode == 0 else "failed",
                    "started_at": started_at,
                    "finished_at": utc_now(),
                    "elapsed_seconds": elapsed,
                    "message": "live weather training finished" if result.returncode == 0 else "live weather training failed",
                    "stdout": result.stdout[-4000:],
                    "stderr": result.stderr[-4000:],
                }
            )
            write_json_atomic(self.status_path, status_payload)
        except Exception as exc:
            self._write_status(
                run_id,
                status="failed",
                started_at=started_at,
                finished_at=utc_now(),
                elapsed_seconds=round(time.perf_counter() - started, 3),
                message=str(exc),
                quality_status="failed",
            )

    def _run_spark(self, run_id: str) -> subprocess.CompletedProcess[str]:
        command = [
            sys.executable,
            "-m",
            "spark_jobs.live_weather",
            "--config",
            str(self._config_path()),
            "--weather-history",
            str(self.weather_history_path),
            "--current-weather",
            str(self.current_weather_path),
            "--forecast-weather",
            str(self.forecast_weather_path),
            "--run-id",
            run_id,
        ]
        return subprocess.run(
            command,
            cwd=self.project_root,
            env=self._env(),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def _load_generated_status(self, run_id: str) -> dict[str, Any]:
        if self.status_path.exists():
            with self.status_path.open("r", encoding="utf-8") as handle:
                existing = json.load(handle)
        else:
            existing = {"run_id": run_id, "job_type": "live_weather_training"}
        generated_path = self.cache_dir / "live_training_status.json"
        if generated_path.exists():
            with generated_path.open("r", encoding="utf-8") as handle:
                generated = json.load(handle)
            return {**existing, **generated}
        return existing

    def _write_status(self, run_id: str, **fields: Any) -> None:
        payload = self.load_status(default_none=True) or {"run_id": run_id, "job_type": "live_weather_training"}
        payload.update(fields)
        payload["run_id"] = run_id
        payload["job_type"] = "live_weather_training"
        write_json_atomic(self.status_path, payload)

    def _config_path(self) -> Path:
        return self.config_path if self.config_path.is_absolute() else self.project_root / self.config_path

    @staticmethod
    def _env() -> dict[str, str]:
        env = os.environ.copy()
        env.setdefault("PYSPARK_PYTHON", sys.executable)
        env.setdefault("PYSPARK_DRIVER_PYTHON", sys.executable)
        return env


def infer_date_range(input_path: str | Path) -> tuple[str, str]:
    if str(input_path).startswith("hdfs://"):
        raise ValueError("cannot infer live weather date range from HDFS path before Spark run; set local input for live demo")
    path = Path(input_path)
    min_date: str | None = None
    max_date: str | None = None
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            event_time = row.get("event_time", "")
            if len(event_time) < 10:
                continue
            dt = event_time[:10]
            min_date = dt if min_date is None or dt < min_date else min_date
            max_date = dt if max_date is None or dt > max_date else max_date
    if not min_date or not max_date:
        raise ValueError(f"cannot infer event date range from {path}")
    return min_date, max_date
