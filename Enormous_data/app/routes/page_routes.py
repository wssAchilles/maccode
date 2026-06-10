from __future__ import annotations

from pathlib import Path

from flask import Blueprint, abort, current_app, render_template, send_from_directory

page_bp = Blueprint("pages", __name__)

REACT_ROUTES = (
    "/affinity",
    "/anomalies",
    "/attribution",
    "/behavior",
    "/cart-recovery",
    "/cohorts",
    "/conversion",
    "/experiments",
    "/feature-mart",
    "/forecasting",
    "/journey",
    "/lifecycle",
    "/optimization",
    "/ops",
    "/portfolio",
    "/quality",
    "/rankings",
    "/recommendations",
)


def frontend_dist() -> Path:
    return Path(current_app.config["PROJECT_ROOT"]) / "frontend" / "dist"


def serve_react_index():
    dist = frontend_dist()
    if not (dist / "index.html").exists():
        abort(404)
    return send_from_directory(dist, "index.html")


@page_bp.route("/")
def index():
    return render_template("index.html")


@page_bp.route("/overview")
def overview():
    return render_template("overview.html")


@page_bp.route("/charts")
def charts():
    return render_template("charts.html")


@page_bp.route("/table")
def table():
    return render_template("table.html")


@page_bp.route("/assets/<path:filename>")
def frontend_asset(filename: str):
    dist = frontend_dist() / "assets"
    if not (dist / filename).exists():
        abort(404)
    return send_from_directory(dist, filename)


@page_bp.route("/favicon.svg")
def frontend_favicon():
    dist = frontend_dist()
    if not (dist / "favicon.svg").exists():
        abort(404)
    return send_from_directory(dist, "favicon.svg")


for route in REACT_ROUTES:
    page_bp.add_url_rule(route, endpoint=f"react_{route.strip('/').replace('-', '_')}", view_func=serve_react_index)
