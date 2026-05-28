from __future__ import annotations

from fastapi import FastAPI

from interfaces.api.routes import ai_report, health, stats, zones


def create_app() -> FastAPI:
    app = FastAPI(title="TrafficPerceptionEngine", version="0.1.0")
    app.include_router(health.router, prefix="/api")
    app.include_router(stats.router, prefix="/api")
    app.include_router(zones.router, prefix="/api")
    app.include_router(ai_report.router, prefix="/api")
    return app


app = create_app()
