from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from flask import Flask, request
from flask_cors import CORS

from app.config import config_from_env
from app.jobs.service import JobNotFoundError
from app.routes.api_routes import api_bp
from app.routes.health_routes import health_bp
from app.routes.page_routes import page_bp
from app.responses import api_error
from app.services.metric_cache import CacheNotReadyError
from app.services.spark_runner import SparkJobRunningError


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_from_env())
    project_root = Path(app.config["PROJECT_ROOT"])
    app.config["PROJECT_ROOT"] = project_root

    CORS(
        app,
        resources={
            r"/api/*": {"origins": app.config["CORS_ALLOWED_ORIGINS"]},
            r"/healthz": {"origins": app.config["CORS_ALLOWED_ORIGINS"]},
            r"/readyz": {"origins": app.config["CORS_ALLOWED_ORIGINS"]},
        },
    )

    @app.before_request
    def assign_request_id():
        from flask import g

        g.request_id = request.headers.get("X-Request-ID") or str(uuid4())

    @app.after_request
    def attach_request_id(response):
        from flask import g

        response.headers["X-Request-ID"] = getattr(g, "request_id", "")
        if request.path.startswith("/api/") and not request.path.startswith("/api/v1/"):
            response.headers["Deprecation"] = "true"
        return response

    app.register_blueprint(page_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(api_bp, url_prefix="/api/v1")
    app.register_blueprint(api_bp, url_prefix="/api", name="api_legacy")

    @app.errorhandler(CacheNotReadyError)
    def handle_cache_not_ready(error: CacheNotReadyError):
        return api_error(str(error), 503, 50301)

    @app.errorhandler(SparkJobRunningError)
    def handle_spark_running(error: SparkJobRunningError):
        return api_error(str(error), 409, 40901)

    @app.errorhandler(JobNotFoundError)
    def handle_job_not_found(error: JobNotFoundError):
        return api_error(str(error), 404, 40401)

    @app.errorhandler(ValueError)
    def handle_value_error(error: ValueError):
        return api_error(str(error), 400, 40001)

    @app.errorhandler(404)
    def handle_not_found(error):
        if request.path.startswith("/api/") or request.path in ("/healthz", "/readyz"):
            return api_error("resource not found", 404, 40401)
        return error

    @app.errorhandler(500)
    def handle_internal_error(error):
        return api_error("internal server error", 500, 50001)

    return app
