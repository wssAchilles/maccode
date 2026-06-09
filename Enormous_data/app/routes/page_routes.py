from __future__ import annotations

from flask import Blueprint, render_template

page_bp = Blueprint("pages", __name__)


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
