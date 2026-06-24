from __future__ import annotations

import argparse
import csv
from pathlib import Path

from app.services.open_meteo import (
    DEFAULT_CITY,
    DEFAULT_LATITUDE,
    DEFAULT_LONGITUDE,
    DEFAULT_TIMEZONE,
    OpenMeteoClient,
    fetch_current_with_cache,
    fetch_historical_with_cache,
    fetch_hourly_forecast_with_cache,
)


def infer_date_range(input_path: str | Path) -> tuple[str, str]:
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch Open-Meteo weather data for live training.")
    parser.add_argument("--input", default="data/sample/ecommerce_user_sample_1pct.csv", help="Ecommerce CSV used to infer dates.")
    parser.add_argument("--start-date", default=None)
    parser.add_argument("--end-date", default=None)
    parser.add_argument("--history-output", default="data/live/weather_history_2019.csv")
    parser.add_argument("--current-output", default="data/live/current_weather.json")
    parser.add_argument("--forecast-output", default="data/live/forecast_weather_24h.json")
    parser.add_argument("--forecast-horizon-hours", default=24, type=int)
    parser.add_argument("--city", default=DEFAULT_CITY)
    parser.add_argument("--latitude", default=DEFAULT_LATITUDE, type=float)
    parser.add_argument("--longitude", default=DEFAULT_LONGITUDE, type=float)
    parser.add_argument("--timezone", default=DEFAULT_TIMEZONE)
    parser.add_argument("--force", action="store_true", help="Force refetch even if cache exists.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    start_date, end_date = (args.start_date, args.end_date) if args.start_date and args.end_date else infer_date_range(args.input)
    client = OpenMeteoClient(
        city=args.city,
        latitude=args.latitude,
        longitude=args.longitude,
        timezone_name=args.timezone,
    )
    historical = fetch_historical_with_cache(
        args.history_output,
        start_date=start_date,
        end_date=end_date,
        client=client,
        force=args.force,
    )
    current = fetch_current_with_cache(args.current_output, client=client, force=args.force)
    forecast = fetch_hourly_forecast_with_cache(
        args.forecast_output,
        client=client,
        force=args.force,
        horizon_hours=args.forecast_horizon_hours,
    )
    print(
        "Open-Meteo weather ready: "
        f"history={historical['source_status']} rows={historical['rows']} "
        f"range={start_date}..{end_date} current={current.get('source_status')} "
        f"forecast={forecast.get('source_status')} hours={len(forecast.get('hourly') or [])}"
    )


if __name__ == "__main__":
    main()
