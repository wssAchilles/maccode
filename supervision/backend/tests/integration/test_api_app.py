from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from application.services.calibration_preset_store import CalibrationPresetStore
from fastapi.testclient import TestClient
from interfaces.api.app import create_app


def test_health_endpoint_reports_service_status() -> None:
    client = TestClient(create_app())

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["data"]["service"] == "TrafficPerceptionEngine"


def test_cors_allows_local_vite_preview_origin() -> None:
    client = TestClient(create_app())

    response = client.options(
        "/api/video/process",
        headers={
            "Origin": "http://127.0.0.1:4173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:4173"


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
    assert payload["calibration_diagnostics"]["reprojection_rmse_px"] >= 0
    assert payload["calibration_diagnostics"]["inlier_count"] >= 4
    assert "detector bounding-box jitter" in payload["calibration_diagnostics"]["error_sources"]
    assert payload["homography_grid"]["generated_from"] == "inverse_homography_projection"
    assert payload["homography_grid"]["lines"]
    assert payload["traffic_flow"]["congestion_level"] in {
        "free_flow",
        "stable_flow",
        "critical_flow",
        "congested_flow",
    }


def test_history_stats_endpoint_allows_full_video_report_window() -> None:
    client = TestClient(create_app())

    response = client.get("/api/stats/history?limit=5000")

    assert response.status_code == 200
    assert isinstance(response.json()["data"], list)


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
    assert "累计进入 **1**" in payload["report_markdown"]
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
    assert task["processed_video_url"] is None

    status_response = client.get(f"/api/video/status/{task['task_id']}")
    assert status_response.status_code == 200
    assert status_response.json()["data"]["frame_count"] >= 1

    stop_response = client.post(f"/api/video/stop/{task['task_id']}")
    assert stop_response.status_code == 200
    assert stop_response.json()["data"]["status"] == "stopped"


def test_video_samples_endpoint_lists_curated_real_clips() -> None:
    client = TestClient(create_app())

    response = client.get("/api/video/samples")

    assert response.status_code == 200
    samples = response.json()["data"]
    assert [sample["name"] for sample in samples] == [
        "026_complex_signal_day_wide_0115s_30s.mp4",
        "042_pedestrian_crowd_high_view_0270s_30s.mp4",
        "054_dense_city_traffic_4k_elevated_0030s_30s.mp4",
        "058_dense_city_traffic_4k_elevated_0150s_30s.mp4",
    ]
    assert all(sample["source"].startswith("file://") for sample in samples)
    assert all(sample["size_bytes"] > 0 for sample in samples)
    assert samples[0]["role"] == "signalized_intersection_vehicle_speed"
    assert samples[0]["tuning"]["confidence_threshold"] == 0.45
    assert samples[0]["tuning"]["runtime_frame_stride"] == 1


def test_video_sample_raw_endpoint_serves_curated_mp4() -> None:
    client = TestClient(create_app())

    response = client.get(
        "/api/video/samples/026_complex_signal_day_wide_0115s_30s.mp4/raw",
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("video/mp4")
    assert len(response.content) > 0


def test_video_sample_raw_endpoint_rejects_path_traversal() -> None:
    client = TestClient(create_app())

    response = client.get("/api/video/samples/..%2Fcalibration_presets.yaml/raw")

    assert response.status_code in {400, 404}


def test_calibration_preset_endpoint_persists_manual_yaml_entry(tmp_path: Path) -> None:
    app = create_app()
    app.state.calibration_preset_store = CalibrationPresetStore(
        tmp_path / "calibration_presets.yaml",
    )
    client = TestClient(app)

    response = client.put(
        "/api/calibration/preset",
        json={
            "clip_name": "demo.mp4",
            "notes": "manual control points",
            "position_rmse_floor_m": 0.5,
            "calibration_scale_uncertainty_pct": 4.0,
            "calibration_trusted": True,
            "scale_prior": {
                "kind": "survey",
                "description": "measured 20m road width from site plan",
            },
            "profile_notes": "fixed camera, all points on flat road plane",
            "road_plane_polygon_pixel": [[100, 600], [500, 600], [450, 300], [150, 300]],
            "road_plane_polygon_world": [[0, 0], [20, 0], [20, 60], [0, 60]],
            "validation_segments": [
                {
                    "name": "independent_midline",
                    "pixel_start": [214.28571429, 428.57142857],
                    "pixel_end": [385.71428571, 428.57142857],
                    "world_start": [5, 30],
                    "world_end": [15, 30],
                },
                {
                    "name": "independent_near_lane_edge",
                    "pixel_start": [210.0, 480.0],
                    "pixel_end": [390.0, 480.0],
                    "world_start": [5, 20],
                    "world_end": [15, 20],
                },
            ],
            "frame_width": 1280,
            "frame_height": 720,
            "points": [
                {"pixel_x": 100, "pixel_y": 600, "world_x": 0, "world_y": 0},
                {"pixel_x": 500, "pixel_y": 600, "world_x": 20, "world_y": 0},
                {"pixel_x": 450, "pixel_y": 300, "world_x": 20, "world_y": 60},
                {"pixel_x": 150, "pixel_y": 300, "world_x": 0, "world_y": 60},
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["source"] == "video_manual_preset"
    assert payload["diagnostics"]["calibration_trusted"] is True
    assert payload["entry"]["scale_prior"]["kind"] == "survey"
    assert payload["entry"]["profile_notes"] == "fixed camera, all points on flat road plane"
    assert payload["entry"]["road_plane_polygon_pixel"] == [
        [100.0, 600.0],
        [500.0, 600.0],
        [450.0, 300.0],
        [150.0, 300.0],
    ]
    assert payload["diagnostics"]["homography_grid"]["lines"]
    get_response = client.get("/api/calibration/preset", params={"clip_name": "demo.mp4"})
    assert get_response.status_code == 200
    assert get_response.json()["data"]["notes"] == "manual control points"
    assert get_response.json()["data"]["scale_prior"]["description"] == (
        "measured 20m road width from site plan"
    )
    saved = yaml.safe_load((tmp_path / "calibration_presets.yaml").read_text())
    assert "demo.mp4" in saved["video_calibrations"]
    assert saved["video_calibrations"]["demo.mp4"]["road_plane_polygon_pixel"]


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
    assert payload["stored_filename"] == "campus-road.mp4"
    assert Path(payload["path"]).name == "campus-road.mp4"
    assert len(Path(payload["path"]).parent.name) == 32
    assert payload["size_bytes"] == len(b"fake-video-bytes")
    assert payload["analysis_status"] == "fallback_demo"
    assert payload["analysis_source"] == "synthetic"
    assert payload["analysis_error"]


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
