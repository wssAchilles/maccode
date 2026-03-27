from __future__ import annotations

from app.ports import PersistenceStatusPort

from .response import component_error, component_ok


async def build_persistence_component(
    persistence_status: PersistenceStatusPort,
    *,
    request_id: str,
) -> dict[str, object]:
    try:
        payload = await persistence_status.get_persistence_status(request_id=request_id)
    except Exception as exc:
        return component_error(
            code="summary_persistence_failed",
            message=f"persistence status unavailable: {exc}",
            request_id=request_id,
            status_code=502,
        )
    return component_ok(payload)
