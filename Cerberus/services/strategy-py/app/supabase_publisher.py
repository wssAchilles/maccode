from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from app.config import settings
from app.schemas import Signal

logger = logging.getLogger(__name__)


class SupabaseSignalPublisher:
    def __init__(self) -> None:
        self.enabled = settings.supabase_enabled
        self._url = settings.supabase_project_url
        self._api_key = settings.supabase_service_role_key
        self._table = settings.supabase_signal_table
        self._client: httpx.AsyncClient | None = None

        if not self.enabled:
            return

        if not self._url or not self._api_key:
            logger.warning("Supabase publisher enabled but missing URL or service role key")
            self.enabled = False
            return

        self._client = httpx.AsyncClient(timeout=settings.supabase_timeout_seconds)
        logger.info("Supabase publisher enabled for table=%s", self._table)

    async def publish_signal(self, signal: Signal) -> None:
        if not self.enabled or self._client is None or not self._url or not self._api_key:
            return

        endpoint = f"{self._url.rstrip('/')}/rest/v1/{self._table}"
        payload: dict[str, Any] = {
            "strategy_id": signal.strategy_id,
            "symbol": signal.symbol,
            "signal": signal.signal,
            "confidence": signal.confidence,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            resp = await self._client.post(
                endpoint,
                headers={
                    "apikey": self._api_key,
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                    "Prefer": "return=minimal",
                },
                json=payload,
            )
            if resp.status_code >= 300:
                logger.warning(
                    "Supabase write failed status=%s body=%s",
                    resp.status_code,
                    resp.text[:300],
                )
        except Exception as exc:
            logger.warning("Supabase write exception: %s", exc)

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
