from __future__ import annotations

import pytest
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
    assert payload["active_tracks"][0]["speed_confidence"] is not None
    assert payload["active_tracks"][0]["speed_uncertainty_kmh"] is not None
    assert payload["calibration_quality"] == "excellent"
    assert payload["traffic_flow"]["congestion_level"] in {
        "free_flow",
        "stable_flow",
        "critical_flow",
        "congested_flow",
    }


def test_ai_report_endpoint_analyzes_frame_report_json(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_ENABLED", "false")
    client = TestClient(create_app())
    frame_report = client.get("/api/stats/realtime").json()["data"]

    response = client.post(
        "/api/ai/report",
        json={
            "stats": frame_report,
            "location_label": "学校门口",
            "scene_tags": ["school_zone", "rain"],
        },
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["provider"] == "rule-based-local"
    assert "累计进入 1" in payload["report_markdown"]
    assert payload["dynamic_context"]["scene"]["location_label"] == "学校门口"
    assert payload["dynamic_context"]["scene"]["scene_tags"] == ["school_zone", "rain"]
    assert "traffic_flow" in payload["dynamic_context"]["physical_state"]
    assert "标定质量" in payload["report_markdown"]


def test_zones_endpoint_returns_default_demo_zone() -> None:
    client = TestClient(create_app())

    response = client.get("/api/zones")

    assert response.status_code == 200
    assert response.json()["data"][0]["name"] == "main_gate"


def test_video_process_lifecycle_creates_and_stops_task() -> None:
    client = TestClient(create_app())

    start_response = client.post("/api/video/process", json={"source": "demo://traffic"})

    assert start_response.status_code == 200
    task = start_response.json()["data"]
    assert task["status"] == "running"

    status_response = client.get(f"/api/video/status/{task['task_id']}")
    assert status_response.status_code == 200
    assert status_response.json()["data"]["frame_count"] >= 1

    stop_response = client.post(f"/api/video/stop/{task['task_id']}")
    assert stop_response.status_code == 200
    assert stop_response.json()["data"]["status"] == "stopped"


def test_video_upload_saves_local_file_and_starts_processing_task() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/video/upload",
        files={"file": ("campus-road.mp4", b"fake-video-bytes", "video/mp4")},
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["task_id"]
    assert payload["status"] == "running"
    assert payload["source"].startswith("file://")
    assert payload["uploaded_filename"] == "campus-road.mp4"
    assert payload["size_bytes"] == len(b"fake-video-bytes")


def test_video_upload_rejects_non_video_extension() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/video/upload",
        files={"file": ("notes.txt", b"not a video", "text/plain")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "unsupported video file type"


def test_history_and_cumulative_stats_are_available_after_processing() -> None:
    client = TestClient(create_app())
    client.post("/api/video/process", json={"source": "demo://traffic"})

    history_response = client.get("/api/stats/history")
    cumulative_response = client.get("/api/stats/cumulative")

    assert history_response.status_code == 200
    assert len(history_response.json()["data"]) >= 1
    assert cumulative_response.status_code == 200
    assert cumulative_response.json()["data"]["total_frames"] >= 1
    assert cumulative_response.json()["data"]["avg_speed_kmh"] > 0


def test_zones_can_be_updated_for_demo_configuration() -> None:
    client = TestClient(create_app())
    zones = [{"name": "north_gate", "line_start": [0, 20], "line_end": [100, 20]}]

    update_response = client.put("/api/zones", json=zones)
    read_response = client.get("/api/zones")

    assert update_response.status_code == 200
    assert update_response.json()["data"][0]["name"] == "north_gate"
    assert read_response.json()["data"][0]["name"] == "north_gate"


def test_websocket_stream_sends_frame_report_message() -> None:
    client = TestClient(create_app())

    with client.websocket_connect("/ws/stream") as websocket:
        message = websocket.receive_json()

    assert message["type"] == "frame_report"
    assert message["data"]["frame_index"] == 3
    assert message["data"]["total_in"] >= 1
