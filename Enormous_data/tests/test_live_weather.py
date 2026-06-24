from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

from app import create_app
from app.services.open_meteo import OpenMeteoClient, OpenMeteoError, fetch_current_with_cache, fetch_hourly_forecast_with_cache, write_historical_csv
from spark_jobs.live_weather import build_current_weather_impact, build_forecast_weather_impact, build_live_weather_outputs


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


@pytest.fixture(scope="module")
def spark():
    os.environ["PYSPARK_PYTHON"] = sys.executable
    session = (
        SparkSession.builder.master("local[2]")
        .appName("live-weather-test")
        .config("spark.ui.enabled", "false")
        .config("spark.sql.shuffle.partitions", "2")
        .getOrCreate()
    )
    yield session
    session.stop()


def test_open_meteo_historical_response_writes_csv(monkeypatch, tmp_path):
    payload = {
        "hourly": {
            "time": ["2019-10-01T00:00", "2019-10-01T01:00"],
            "temperature_2m": [20.0, 21.0],
            "relative_humidity_2m": [70, 72],
            "precipitation": [0.0, 0.1],
            "rain": [0.0, 0.1],
            "weather_code": [0, 61],
            "wind_speed_10m": [5.0, 6.0],
        }
    }
    monkeypatch.setattr("app.services.open_meteo.requests.get", lambda *args, **kwargs: FakeResponse(payload))

    result = OpenMeteoClient().fetch_historical("2019-10-01", "2019-10-01")
    output = tmp_path / "weather.csv"
    rows = write_historical_csv(output, result)

    assert rows == 2
    assert "temperature_2m" in output.read_text(encoding="utf-8")


def test_current_weather_uses_cache_when_network_fails(monkeypatch, tmp_path):
    output = tmp_path / "current_weather.json"
    output.write_text(json.dumps({"city": "上海", "source_status": "network", "current": {"temperature_2m": 25}}), encoding="utf-8")

    def fail(*args, **kwargs):
        raise OpenMeteoError("network down")

    monkeypatch.setattr("app.services.open_meteo.OpenMeteoClient.fetch_current", fail)

    payload = fetch_current_with_cache(output, force=True)

    assert payload["source_status"] == "cache"
    assert payload["current"]["temperature_2m"] == 25


def test_open_meteo_hourly_forecast_response_and_cache(monkeypatch, tmp_path):
    payload = {
        "hourly": {
            "time": ["2026-06-16T10:00", "2026-06-16T11:00"],
            "temperature_2m": [24.0, 25.0],
            "relative_humidity_2m": [80, 78],
            "precipitation": [0.1, 0.0],
            "rain": [0.1, 0.0],
            "weather_code": [61, 3],
            "wind_speed_10m": [10.0, 11.0],
        },
        "hourly_units": {"temperature_2m": "°C"},
    }
    monkeypatch.setattr("app.services.open_meteo.requests.get", lambda *args, **kwargs: FakeResponse(payload))

    output = tmp_path / "forecast.json"
    result = fetch_hourly_forecast_with_cache(
        output,
        client=OpenMeteoClient(),
        force=True,
        horizon_hours=2,
        start_time="2026-06-16T10:00",
    )
    cached = fetch_hourly_forecast_with_cache(output, client=OpenMeteoClient(), force=False, horizon_hours=2)

    assert result["source_status"] == "network"
    assert result["hourly"][0]["time"] == "2026-06-16T10:00"
    assert cached["source_status"] == "cache"


def test_live_weather_outputs_join_quality_and_model_comparison(spark, tmp_path):
    events = []
    for day in range(1, 10):
        price = 100.0 + day * 10
        for category in ["electronics", "apparel"]:
            events.append(
                {
                    "event_time": f"2019-10-{day:02d} 10:00:00",
                    "event_type": "purchase",
                    "product_id": day,
                    "category_id": day,
                    "category_code": category,
                    "brand": "brand",
                    "price": price,
                    "user_id": day,
                    "user_session": f"s-{category}-{day}",
                }
            )
            events.append(
                {
                    "event_time": f"2019-10-{day:02d} 09:00:00",
                    "event_type": "view",
                    "product_id": day,
                    "category_id": day,
                    "category_code": category,
                    "brand": "brand",
                    "price": price,
                    "user_id": day + 100,
                    "user_session": f"v-{category}-{day}",
                }
            )
    df = (
        spark.createDataFrame(events)
        .withColumn("event_timestamp", F.to_timestamp("event_time"))
        .withColumn("category_level1", F.split("category_code", r"\.").getItem(0))
    )
    weather_path = tmp_path / "weather.csv"
    weather_path.write_text(
        "\n".join(
            ["time,city,latitude,longitude,temperature_2m,relative_humidity_2m,precipitation,rain,weather_code,wind_speed_10m"]
            + [f"2019-10-{day:02d}T00:00,上海,31.2,121.4,{20 + day},70,0,0,0,5" for day in range(1, 10)]
        ),
        encoding="utf-8",
    )

    metrics = build_live_weather_outputs(
        df,
        weather_path,
        {"city": "上海", "source_status": "network", "current": {"temperature_2m": 30, "precipitation": 0, "relative_humidity_2m": 70, "wind_speed_10m": 6}},
        {"live_weather": {"top_categories": 2, "backtest_days": 3}},
        run_id="live-test",
        input_snapshot={"actual_input_path": "fixture.csv"},
    )

    summary = metrics["live_weather_summary"]
    assert summary["join_coverage_rate"] == 1
    assert summary["current_weather_used_for_training"] is False
    assert {row["model_name"] for row in metrics["live_training_metrics"]["model_metrics"]} == {
        "baseline_history",
        "weather_enhanced",
    }
    assert metrics["live_weather_impact"]["items"]


def test_current_weather_impact_uses_category_specific_weather_response():
    joined_rows = []
    for day in range(1, 8):
        temp = 18 + day
        for category, gmv in {
            "electronics": 100 + day * 20,
            "apparel": 260 - day * 18,
            "appliances": 180 + (day % 2) * 12,
        }.items():
            joined_rows.append(
                {
                    "dt": f"2019-10-{day:02d}",
                    "scope": "category",
                    "entity_key": category,
                    "entity_label": category,
                    "gmv": float(gmv),
                    "temperature_2m": float(temp),
                    "relative_humidity_2m": 70.0,
                    "precipitation": 0.0,
                    "rain": 0.0,
                    "weather_code": 0.0,
                    "wind_speed_10m": 5.0,
                }
            )

    impact = build_current_weather_impact(
        joined_rows,
        {
            "city": "上海",
            "source_status": "network",
            "current": {
                "time": "2026-06-16T09:00",
                "temperature_2m": 30.0,
                "relative_humidity_2m": 70.0,
                "precipitation": 0.0,
                "rain": 0.0,
                "weather_code": 0.0,
                "wind_speed_10m": 5.0,
            },
        },
        {"comparison_status": "improved"},
        "impact-test",
    )

    scores = {row["entity_key"]: row["impact_score"] for row in impact["items"]}
    assert scores["electronics"] > 0
    assert scores["apparel"] < 0
    assert len({round(value, 2) for value in scores.values()}) > 1


def test_forecast_weather_impact_outputs_hourly_curve():
    joined_rows = []
    for day in range(1, 8):
        for category, gmv in {"electronics": 100 + day * 15, "apparel": 220 - day * 10}.items():
            joined_rows.append(
                {
                    "dt": f"2019-10-{day:02d}",
                    "scope": "category",
                    "entity_key": category,
                    "entity_label": category,
                    "gmv": float(gmv),
                    "temperature_2m": float(18 + day),
                    "relative_humidity_2m": 70.0,
                    "precipitation": 1.0 if day % 2 else 0.0,
                    "rain": 1.0 if day % 2 else 0.0,
                    "weather_code": 61.0 if day % 2 else 3.0,
                    "wind_speed_10m": 5.0,
                }
            )
    forecast = {
        "city": "上海",
        "source_status": "network",
        "hourly": [
            {"time": f"2026-06-16T{hour:02d}:00", "temperature_2m": 26.0, "relative_humidity_2m": 80.0, "precipitation": 1.0 if hour % 2 else 0.0, "rain": 0.0, "weather_code": 61.0, "wind_speed_10m": 9.0}
            for hour in range(4)
        ],
    }

    impact = build_forecast_weather_impact(joined_rows, forecast, run_id="forecast-test", horizon_hours=4)

    assert impact["training_uses_forecast_weather"] is False
    assert len(impact["items"]) == 4
    assert impact["items"][0]["category_impacts"]
    assert impact["summary"]["peak_abs_hour"] is not None


def test_live_weather_api_returns_envelopes(monkeypatch, tmp_path):
    cache_dir = tmp_path / "cache"
    live_dir = tmp_path / "live"
    cache_dir.mkdir()
    live_dir.mkdir()
    (live_dir / "current_weather.json").write_text(
        json.dumps({"city": "上海", "source_status": "cache", "current": {"temperature_2m": 26}}),
        encoding="utf-8",
    )
    (live_dir / "forecast_weather_24h.json").write_text(
        json.dumps({"city": "上海", "source_status": "cache", "hourly": [{"time": "2026-06-16T10:00"}]}),
        encoding="utf-8",
    )
    for name, payload in {
        "live_weather_summary": {"join_coverage_rate": 1},
        "live_training_status": {"run_id": "live-test", "status": "succeeded"},
        "live_training_metrics": {"model_metrics": []},
        "live_weather_impact": {"items": []},
        "live_weather_forecast_impact": {"items": [], "training_uses_forecast_weather": False},
    }.items():
        (cache_dir / f"{name}.json").write_text(json.dumps(payload), encoding="utf-8")

    app = create_app()
    app.config.update(
        TESTING=True,
        METRIC_CACHE_DIR=cache_dir,
        LIVE_DATA_DIR=live_dir,
        RAW_DATA_PATH=tmp_path / "events.csv",
        SPARK_CONFIG_PATH=tmp_path / "local.yaml",
    )
    client = app.test_client()

    assert client.get("/api/v1/live-weather/current").json["data"]["current"]["temperature_2m"] == 26
    assert client.get("/api/v1/live-weather/forecast").json["data"]["hourly"][0]["time"] == "2026-06-16T10:00"
    assert client.get("/api/v1/live-weather/summary").json["data"]["join_coverage_rate"] == 1
    assert client.get("/api/v1/live-training/status").json["data"]["status"] == "succeeded"
    assert client.get("/api/v1/live-training/forecast-impact").json["data"]["training_uses_forecast_weather"] is False

    monkeypatch.setattr(
        "app.routes.api_routes.LiveWeatherService.enqueue_refresh",
        lambda self: {"status": "queued", "run_id": "next-run"},
    )
    response = client.post("/api/v1/live-training/refresh")
    assert response.status_code == 202
    assert response.json["data"]["run_id"] == "next-run"
