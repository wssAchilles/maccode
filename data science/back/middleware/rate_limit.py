"""Rate limiting with in-memory and Firestore backends."""

from __future__ import annotations

import hashlib
import time
from collections import defaultdict
from functools import wraps
from threading import Lock

from flask import current_app, jsonify, request
from google.cloud import firestore
from google.cloud.firestore_v1 import SERVER_TIMESTAMP

from config import Config


class MemoryRateLimiter:
    def __init__(self, cleanup_interval: int = 300):
        self.requests = defaultdict(list)
        self.lock = Lock()
        self.cleanup_interval = cleanup_interval
        self.last_cleanup = time.time()

    def _cleanup_stale_keys(self, window_seconds: int = 60):
        now = time.time()
        if now - self.last_cleanup < self.cleanup_interval:
            return
        self.last_cleanup = now
        window_start = now - window_seconds
        keys_to_delete = []
        for key, timestamps in self.requests.items():
            if not timestamps or all(ts <= window_start for ts in timestamps):
                keys_to_delete.append(key)
        for key in keys_to_delete:
            del self.requests[key]

    def is_allowed(self, key: str, max_requests: int = 100, window_seconds: int = 60) -> bool:
        with self.lock:
            now = time.time()
            window_start = now - window_seconds
            self._cleanup_stale_keys(window_seconds)
            self.requests[key] = [ts for ts in self.requests[key] if ts > window_start]
            if len(self.requests[key]) >= max_requests:
                return False
            self.requests[key].append(now)
            return True


class FirestoreRateLimiter:
    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None:
            self._client = firestore.Client(database=Config.FIRESTORE_DATABASE)
        return self._client

    def is_allowed(self, key: str, max_requests: int = 100, window_seconds: int = 60) -> bool:
        now = time.time()
        window_start = now - window_seconds
        doc_id = hashlib.sha256(key.encode('utf-8')).hexdigest()
        ref = self._get_client().collection('_rate_limits').document(doc_id)
        snapshot = ref.get()
        data = snapshot.to_dict() if snapshot.exists else {}
        timestamps = [ts for ts in data.get('timestamps', []) if isinstance(ts, (int, float)) and ts > window_start]
        if len(timestamps) >= max_requests:
            return False
        timestamps.append(now)
        ref.set(
            {
                'key': key,
                'timestamps': timestamps,
                'updated_at': SERVER_TIMESTAMP,
            },
            merge=True,
        )
        return True


_memory_rate_limiter = MemoryRateLimiter()
_firestore_rate_limiter = FirestoreRateLimiter()


def _get_rate_limiter():
    backend = current_app.config.get('RATE_LIMIT_BACKEND', 'memory')
    if backend == 'firestore' and not current_app.config.get('TESTING'):
        return _firestore_rate_limiter
    return _memory_rate_limiter


def rate_limit(max_requests: int = 100, window_seconds: int = 60):
    def decorator(func):
        @wraps(func)
        def decorated_function(*args, **kwargs):
            if current_app.config.get('TESTING'):
                return func(*args, **kwargs)

            if hasattr(request, 'user') and request.user:
                key = f"user:{request.user.get('uid')}"
            else:
                key = f"ip:{request.remote_addr}"

            limiter = _get_rate_limiter()
            try:
                allowed = limiter.is_allowed(key, max_requests, window_seconds)
            except Exception:
                allowed = _memory_rate_limiter.is_allowed(key, max_requests, window_seconds)

            if not allowed:
                return jsonify(
                    {
                        'success': False,
                        'error': {
                            'code': 'RATE_LIMIT_EXCEEDED',
                            'message': f'Too many requests. Limit: {max_requests} per {window_seconds}s',
                        },
                        'meta': {},
                    }
                ), 429

            return func(*args, **kwargs)

        return decorated_function

    return decorator
