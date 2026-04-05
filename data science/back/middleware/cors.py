"""Explicit CORS middleware for browser-facing API routes."""

from __future__ import annotations

from flask import Flask, request


def configure_cors(app: Flask) -> None:
    allowed_origins = {
        str(origin).strip()
        for origin in app.config.get('CORS_ORIGINS', [])
        if str(origin).strip()
    }
    allowed_methods = [
        str(method).upper().strip()
        for method in app.config.get('CORS_METHODS', ['GET', 'POST', 'OPTIONS'])
        if str(method).strip()
    ]
    base_allowed_headers = {
        str(header).strip()
        for header in app.config.get('CORS_ALLOW_HEADERS', ['Content-Type', 'Authorization'])
        if str(header).strip()
    }
    supports_credentials = bool(app.config.get('CORS_SUPPORTS_CREDENTIALS', True))

    def _origin_is_allowed(origin: str | None) -> bool:
        return bool(origin and origin in allowed_origins)

    def _apply_headers(response):
        origin = request.headers.get('Origin')
        if not _origin_is_allowed(origin):
            return response

        request_headers = {
            item.strip()
            for item in str(request.headers.get('Access-Control-Request-Headers') or '').split(',')
            if item.strip()
        }
        allow_headers = sorted(base_allowed_headers | request_headers)

        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Credentials'] = 'true' if supports_credentials else 'false'
        response.headers['Access-Control-Allow-Headers'] = ', '.join(allow_headers)
        response.headers['Access-Control-Allow-Methods'] = ', '.join(allowed_methods)
        response.headers['Access-Control-Max-Age'] = '3600'
        response.headers.add('Vary', 'Origin')
        return response

    @app.before_request
    def _handle_preflight():
        if request.method != 'OPTIONS':
            return None
        response = app.make_default_options_response()
        return _apply_headers(response)

    @app.after_request
    def _add_cors_headers(response):
        return _apply_headers(response)
