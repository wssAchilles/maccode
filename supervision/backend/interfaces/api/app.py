from __future__ import annotations

from application.services.runtime_state import DemoRuntime
from fastapi import FastAPI

from interfaces.api.routes import ai_report, health, stats, video, zones
from interfaces.websocket import routes as websocket_routes


def create_app() -> FastAPI:
    app = FastAPI(title="TrafficPerceptionEngine", version="0.1.0")
    app.state.runtime = DemoRuntime()
    app.include_router(health.router, prefix="/api")
    app.include_router(video.router, prefix="/api")
    app.include_router(stats.router, prefix="/api")
    app.include_router(zones.router, prefix="/api")
    app.include_router(ai_report.router, prefix="/api")
    app.include_router(websocket_routes.router)
    return app


app = create_app()
