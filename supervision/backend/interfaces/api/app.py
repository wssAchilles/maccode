from __future__ import annotations

from pathlib import Path

from application.services.calibration_preset_store import CalibrationPresetStore
from application.services.runtime_state import DemoRuntime
from application.services.video_upload_store import LocalVideoUploadStore
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from interfaces.api.routes import ai_report, calibration, health, stats, video, zones
from interfaces.websocket import routes as websocket_routes

PROJECT_ROOT = Path(__file__).resolve().parents[3]
MEDIA_ROOT = PROJECT_ROOT / "data/outputs"


def create_app() -> FastAPI:
    app = FastAPI(title="TrafficPerceptionEngine", version="0.1.0")
    MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"^http://(127\.0\.0\.1|localhost):\d+$",
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.calibration_preset_store = CalibrationPresetStore()
    app.state.runtime = DemoRuntime()
    app.state.video_upload_store = LocalVideoUploadStore()
    app.include_router(health.router, prefix="/api")
    app.include_router(video.router, prefix="/api")
    app.include_router(stats.router, prefix="/api")
    app.include_router(zones.router, prefix="/api")
    app.include_router(calibration.router, prefix="/api")
    app.include_router(ai_report.router, prefix="/api")
    app.include_router(websocket_routes.router)
    app.mount("/media", StaticFiles(directory=str(MEDIA_ROOT)), name="media")
    return app


app = create_app()
