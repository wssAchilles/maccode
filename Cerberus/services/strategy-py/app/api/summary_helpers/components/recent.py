from __future__ import annotations

from app.signal_store import SignalStore

from ..types import SummarySource
from .response import component_error, component_ok


async def build_recent_signals_component(
    signal_store: SignalStore,
    *,
    limit: int,
    source: SummarySource,
    request_id: str,
) -> dict[str, object]:
    try:
        used_source, records = await signal_store.list_recent(limit=limit, source=source)
    except Exception as exc:
        return component_error(
            code="summary_recent_signals_failed",
            message=f"recent signals unavailable: {exc}",
            request_id=request_id,
            status_code=502,
        )

    return component_ok(
        {
            "source": used_source,
            "count": len(records),
            "signals": [item.model_dump() for item in records],
        }
    )
