from __future__ import annotations

import logging

import httpx

from app.config import settings
from app.schemas import SignalRecord

logger = logging.getLogger(__name__)


def build_supabase_client() -> httpx.AsyncClient | None:
    if not supabase_enabled():
        return None
    logger.info("SignalStore using Supabase table=%s", settings.supabase_signal_table)
    return httpx.AsyncClient(timeout=settings.supabase_timeout_seconds)


def supabase_enabled() -> bool:
    return (
        settings.supabase_enabled
        and bool(settings.supabase_project_url)
        and bool(settings.supabase_service_role_key)
    )


async def list_recent_supabase(
    client: httpx.AsyncClient | None,
    *,
    limit: int,
) -> list[SignalRecord] | None:
    if (
        client is None
        or not settings.supabase_project_url
        or not settings.supabase_service_role_key
    ):
        return None

    endpoint = (
        f"{settings.supabase_project_url.rstrip('/')}/rest/v1/{settings.supabase_signal_table}"
    )
    try:
        resp = await client.get(
            endpoint,
            headers={
                "apikey": settings.supabase_service_role_key,
                "Authorization": f"Bearer {settings.supabase_service_role_key}",
            },
            params={
                "select": "strategy_id,symbol,signal,confidence,created_at",
                "order": "created_at.desc",
                "limit": str(limit),
            },
        )
        if resp.status_code >= 300:
            logger.warning(
                "SignalStore supabase read failed status=%s body=%s",
                resp.status_code,
                resp.text[:200],
            )
            return None
        payload = resp.json()
        if not isinstance(payload, list):
            return []
        records: list[SignalRecord] = []
        for row in payload:
            if not isinstance(row, dict):
                continue
            try:
                records.append(SignalRecord.model_validate(row))
            except Exception:
                continue
        return records
    except Exception as exc:
        logger.warning("SignalStore supabase read exception: %s", exc)
        return None
