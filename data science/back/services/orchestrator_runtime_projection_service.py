"""Fetch Rust control-plane runtime projection for shell snapshot aggregation."""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import Any, Dict

from config import Config


class OrchestratorRuntimeProjectionUnavailableError(RuntimeError):
    """Raised when the Rust control-plane projection is unavailable."""


class OrchestratorRuntimeProjectionService:
    """Fetch runtime projection snapshots exposed by the Rust orchestrator."""

    @classmethod
    def get_snapshot(cls, uid: str, *, force_refresh: bool = False) -> Dict[str, Any]:
        orchestrator_url = str(Config.ORCHESTRATOR_BASE_URL or '').strip().rstrip('/')
        if not orchestrator_url:
            raise OrchestratorRuntimeProjectionUnavailableError(
                'Rust orchestrator not configured',
            )

        query = {'uid': uid}
        if force_refresh:
            query['fresh'] = '1'
        request = urllib.request.Request(
            f'{orchestrator_url}/internal/runtime/snapshot?{urllib.parse.urlencode(query)}',
            headers={
                'Accept': 'application/json',
                'X-Internal-Job-Token': Config.INTERNAL_JOB_TOKEN,
            },
            method='GET',
        )
        try:
            with urllib.request.urlopen(
                request,
                timeout=max(float(Config.ORCHESTRATOR_REQUEST_TIMEOUT_S), 1.0),
            ) as response:
                body = response.read().decode('utf-8')
        except Exception as exc:  # pragma: no cover - urllib branch differences
            raise OrchestratorRuntimeProjectionUnavailableError(str(exc)) from exc

        try:
            payload = json.loads(body or '{}')
        except json.JSONDecodeError as exc:
            raise OrchestratorRuntimeProjectionUnavailableError(
                'invalid orchestrator runtime projection payload',
            ) from exc

        if not isinstance(payload, dict):
            raise OrchestratorRuntimeProjectionUnavailableError(
                'invalid orchestrator runtime projection payload',
            )

        if 'projection_version' in payload:
            return payload

        if not payload.get('success'):
            error = payload.get('error') if isinstance(payload.get('error'), dict) else {}
            message = str(error.get('message') or 'orchestrator runtime projection failed')
            raise OrchestratorRuntimeProjectionUnavailableError(message)

        data = payload.get('data')
        if not isinstance(data, dict):
            raise OrchestratorRuntimeProjectionUnavailableError(
                'orchestrator runtime projection data missing',
            )
        return data
