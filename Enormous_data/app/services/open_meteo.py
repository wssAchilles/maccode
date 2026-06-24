from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import requests

from spark_jobs.writers import write_json_atomic


DEFAULT_CITY = "上海"
DEFAULT_LATITUDE = 31.2304
DEFAULT_LONGITUDE = 121.4737
DEFAULT_TIMEZONE = "Asia/Shanghai"
HISTORICAL_ENDPOINT = "https://archive-api.open-meteo.com/v1/archive"
FORECAST_ENDPOINT = "https://api.open-meteo.com/v1/forecast"
WEATHER_VARIABLES = [
    "temperature_2m",
    "relative_humidity_2m",
    "precipitation",
    "rain",
    "weather_code",
    "wind_speed_10m",
]


class OpenMeteoError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class OpenMeteoClient:
    def __init__(
        self,
        *,
        latitude: float = DEFAULT_LATITUDE,
        longitude: float = DEFAULT_LONGITUDE,
        timezone_name: str = DEFAULT_TIMEZONE,
        city: str = DEFAULT_CITY,
        timeout_seconds: float = 20.0,
    ):
        self.latitude = latitude
        self.longitude = longitude
        self.timezone_name = timezone_name
        self.city = city
        self.timeout_seconds = timeout_seconds

    def fetch_historical(self, start_date: str, end_date: str) -> dict[str, Any]:
        payload = self._get_json(
            HISTORICAL_ENDPOINT,
            {
                "latitude": self.latitude,
                "longitude": self.longitude,
                "start_date": start_date,
                "end_date": end_date,
                "hourly": ",".join(WEATHER_VARIABLES),
                "timezone": self.timezone_name,
            },
        )
        return {
            "city": self.city,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "timezone": self.timezone_name,
            "start_date": start_date,
            "end_date": end_date,
            "fetched_at": utc_now(),
            "source_status": "network",
            "payload": payload,
        }

    def fetch_current(self) -> dict[str, Any]:
        payload = self._get_json(
            FORECAST_ENDPOINT,
            {
                "latitude": self.latitude,
                "longitude": self.longitude,
                "current": ",".join(WEATHER_VARIABLES),
                "hourly": ",".join(WEATHER_VARIABLES),
                "forecast_days": 1,
                "timezone": self.timezone_name,
            },
        )
        current = dict(payload.get("current") or {})
        return {
            "city": self.city,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "timezone": self.timezone_name,
            "fetched_at": utc_now(),
            "source_status": "network",
            "current": current,
            "current_units": payload.get("current_units") or {},
            "hourly_units": payload.get("hourly_units") or {},
        }

    def fetch_hourly_forecast(self, *, forecast_days: int = 2, horizon_hours: int = 24, start_time: str | None = None) -> dict[str, Any]:
        payload = self._get_json(
            FORECAST_ENDPOINT,
            {
                "latitude": self.latitude,
                "longitude": self.longitude,
                "hourly": ",".join(WEATHER_VARIABLES),
                "forecast_days": forecast_days,
                "timezone": self.timezone_name,
            },
        )
        hourly = payload.get("hourly") or {}
        times = hourly.get("time") or []
        window_start = start_time or forecast_window_start(self.timezone_name)
        selected = [(index, time_value) for index, time_value in enumerate(times) if str(time_value) >= window_start][:horizon_hours]
        rows = []
        for index, time_value in selected:
            row = {"time": time_value}
            for variable in WEATHER_VARIABLES:
                values = hourly.get(variable) or []
                row[variable] = values[index] if index < len(values) else None
            rows.append(row)
        return {
            "city": self.city,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "timezone": self.timezone_name,
            "fetched_at": utc_now(),
            "source_status": "network",
            "horizon_hours": horizon_hours,
            "forecast_window_start": window_start,
            "forecast_window_end": rows[-1]["time"] if rows else None,
            "hourly": rows,
            "hourly_units": payload.get("hourly_units") or {},
        }

    def _get_json(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        try:
            response = requests.get(url, params=params, timeout=self.timeout_seconds)
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            raise OpenMeteoError(f"failed to fetch Open-Meteo data: {exc}") from exc
        except ValueError as exc:
            raise OpenMeteoError("failed to decode Open-Meteo JSON response") from exc
        if payload.get("error"):
            raise OpenMeteoError(str(payload.get("reason") or "Open-Meteo returned an error"))
        return payload


def write_historical_csv(path: str | Path, historical: dict[str, Any]) -> int:
    payload = historical.get("payload") or {}
    hourly = payload.get("hourly") or {}
    times = hourly.get("time") or []
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "time",
                "city",
                "latitude",
                "longitude",
                "temperature_2m",
                "relative_humidity_2m",
                "precipitation",
                "rain",
                "weather_code",
                "wind_speed_10m",
            ],
        )
        writer.writeheader()
        for index, time_value in enumerate(times):
            row = {
                "time": time_value,
                "city": historical.get("city", DEFAULT_CITY),
                "latitude": historical.get("latitude", DEFAULT_LATITUDE),
                "longitude": historical.get("longitude", DEFAULT_LONGITUDE),
            }
            for variable in WEATHER_VARIABLES:
                values = hourly.get(variable) or []
                row[variable] = values[index] if index < len(values) else None
            writer.writerow(row)
    return len(times)


def fetch_historical_with_cache(
    output_path: str | Path,
    *,
    start_date: str,
    end_date: str,
    client: OpenMeteoClient | None = None,
    force: bool = False,
) -> dict[str, Any]:
    target = Path(output_path)
    if target.exists() and not force:
        return {
            "source_status": "cache",
            "path": str(target),
            "rows": max(0, sum(1 for _ in target.open("r", encoding="utf-8")) - 1),
            "city": DEFAULT_CITY,
            "start_date": start_date,
            "end_date": end_date,
        }
    client = client or OpenMeteoClient()
    historical = client.fetch_historical(start_date, end_date)
    rows = write_historical_csv(target, historical)
    return {
        "source_status": historical["source_status"],
        "path": str(target),
        "rows": rows,
        "city": historical["city"],
        "start_date": start_date,
        "end_date": end_date,
        "fetched_at": historical["fetched_at"],
    }


def fetch_current_with_cache(
    output_path: str | Path,
    *,
    client: OpenMeteoClient | None = None,
    force: bool = False,
) -> dict[str, Any]:
    target = Path(output_path)
    client = client or OpenMeteoClient()
    if force or not target.exists():
        try:
            payload = client.fetch_current()
            write_json_atomic(target, payload)
            return payload
        except OpenMeteoError:
            if target.exists():
                with target.open("r", encoding="utf-8") as handle:
                    payload = json.load(handle)
                payload["source_status"] = "cache"
                return payload
            if not target.exists():
                unavailable = {
                    "city": DEFAULT_CITY,
                    "latitude": DEFAULT_LATITUDE,
                    "longitude": DEFAULT_LONGITUDE,
                    "timezone": DEFAULT_TIMEZONE,
                    "fetched_at": utc_now(),
                    "source_status": "unavailable",
                    "current": {},
                    "current_units": {},
                }
                write_json_atomic(target, unavailable)
                return unavailable
            raise
    with target.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    payload["source_status"] = "cache"
    return payload


def fetch_hourly_forecast_with_cache(
    output_path: str | Path,
    *,
    client: OpenMeteoClient | None = None,
    force: bool = False,
    horizon_hours: int = 24,
    start_time: str | None = None,
) -> dict[str, Any]:
    target = Path(output_path)
    client = client or OpenMeteoClient()
    if force or not target.exists():
        try:
            payload = client.fetch_hourly_forecast(horizon_hours=horizon_hours, start_time=start_time)
            write_json_atomic(target, payload)
            return payload
        except OpenMeteoError:
            if target.exists():
                with target.open("r", encoding="utf-8") as handle:
                    payload = json.load(handle)
                payload["source_status"] = "cache"
                return payload
            unavailable = {
                "city": DEFAULT_CITY,
                "latitude": DEFAULT_LATITUDE,
                "longitude": DEFAULT_LONGITUDE,
                "timezone": DEFAULT_TIMEZONE,
                "fetched_at": utc_now(),
                "source_status": "unavailable",
                "horizon_hours": horizon_hours,
                "forecast_window_start": start_time or forecast_window_start(DEFAULT_TIMEZONE),
                "forecast_window_end": None,
                "hourly": [],
                "hourly_units": {},
            }
            write_json_atomic(target, unavailable)
            return unavailable
    with target.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    payload["source_status"] = "cache"
    return payload


def forecast_window_start(timezone_name: str) -> str:
    now = datetime.now(ZoneInfo(timezone_name)).replace(second=0, microsecond=0)
    if now.minute:
        now = now.replace(minute=0)
        from datetime import timedelta

        now = now + timedelta(hours=1)
    else:
        now = now.replace(minute=0)
    return now.strftime("%Y-%m-%dT%H:%M")
