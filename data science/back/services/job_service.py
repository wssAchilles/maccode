"""Compatibility wrapper for the unified operation service."""

from __future__ import annotations

from services.operation_service import (
    JobBackendUnavailableError,
    JobQueryIndexRequiredError,
    OperationCancelledError,
    OperationService,
)


class JobService(OperationService):
    """Backward-compatible alias for the unified operation service."""

    pass


__all__ = [
    'JobBackendUnavailableError',
    'JobQueryIndexRequiredError',
    'OperationCancelledError',
    'JobService',
]
