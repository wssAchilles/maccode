"""Structured request logging."""

from __future__ import annotations

import json
import logging
import time
import uuid
from functools import wraps

from flask import g, request

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _emit(level: str, **fields):
    payload = json.dumps(fields, ensure_ascii=False, default=str)
    getattr(logger, level.lower(), logger.info)(payload)


def setup_logging(app):
    @app.before_request
    def before_request():
        g.start_time = time.time()
        g.request_id = request.headers.get('X-Request-ID') or str(uuid.uuid4())
        g.user_id = None
        _emit(
            'info',
            event='request_started',
            request_id=g.request_id,
            route=request.path,
            method=request.method,
            user_id=g.user_id,
        )

    @app.after_request
    def after_request(response):
        elapsed = None
        if hasattr(g, 'start_time'):
            elapsed = int((time.time() - g.start_time) * 1000)
        response.headers['X-Request-ID'] = getattr(g, 'request_id', 'unknown')
        _emit(
            'info',
            event='request_finished',
            request_id=getattr(g, 'request_id', 'unknown'),
            route=request.path,
            method=request.method,
            status_code=response.status_code,
            duration_ms=elapsed,
            user_id=getattr(request, 'user', {}).get('uid') if hasattr(request, 'user') else None,
        )
        return response

    @app.errorhandler(Exception)
    def handle_exception(exc):
        _emit(
            'error',
            event='request_failed',
            request_id=getattr(g, 'request_id', 'unknown'),
            route=request.path,
            method=request.method,
            duration_ms=int((time.time() - g.start_time) * 1000) if hasattr(g, 'start_time') else None,
            user_id=getattr(request, 'user', {}).get('uid') if hasattr(request, 'user') else None,
            error=str(exc),
        )
        raise


def log_function_call(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        _emit('info', event='function_call', function=func.__name__)
        return func(*args, **kwargs)

    return wrapper
