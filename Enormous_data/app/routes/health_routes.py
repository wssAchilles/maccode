from __future__ import annotations

from flask import Blueprint, current_app

from app.responses import api_ok

health_bp = Blueprint("health", __name__)


@health_bp.get("/healthz")
def healthz():
    return api_ok(
        {
            "status": "ok",
            "service": current_app.config["SERVICE_NAME"],
            "version": current_app.config["API_VERSION"],
        }
    )


@health_bp.get("/readyz")
def readyz():
    cache_dir = current_app.config["METRIC_CACHE_DIR"]
    raw_data = current_app.config["RAW_DATA_PATH"]
    checks = {
        "cache_dir": cache_dir.exists(),
        "summary_cache": (cache_dir / "summary.json").exists(),
        "raw_data": raw_data.exists(),
    }
    ready = all(checks.values())
    status = 200 if ready else 503
    return api_ok(
        {
            "status": "ready" if ready else "not_ready",
            "service": current_app.config["SERVICE_NAME"],
            "version": current_app.config["API_VERSION"],
            "checks": checks,
        }
    ), status
