from __future__ import annotations

from fastapi.testclient import TestClient

from interfaces.api.app import create_app


def test_health_endpoint_reports_service_status() -> None:
    client = TestClient(create_app())

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["data"]["service"] == "TrafficPerceptionEngine"


def test_realtime_stats_endpoint_returns_frame_report_contract() -> None:
    client = TestClient(create_app())

    response = client.get("/api/stats/realtime")

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["frame_index"] == 3
    assert payload["total_in"] == 1
    assert payload["active_tracks"][0]["speed_kmh"] > 0


def test_ai_report_endpoint_analyzes_frame_report_json() -> None:
    client = TestClient(create_app())
    frame_report = client.get("/api/stats/realtime").json()["data"]

    response = client.post("/api/ai/report", json={"stats": frame_report})

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["provider"] == "rule-based-local"
    assert "累计进入 1" in payload["report_markdown"]


def test_zones_endpoint_returns_default_demo_zone() -> None:
    client = TestClient(create_app())

    response = client.get("/api/zones")

    assert response.status_code == 200
    assert response.json()["data"][0]["name"] == "main_gate"
