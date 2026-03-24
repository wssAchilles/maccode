from __future__ import annotations

import asyncio
import logging
from typing import Any, Literal

import firebase_admin
import httpx
from firebase_admin import firestore

from app.config import settings
from app.schemas import SignalRecord

logger = logging.getLogger(__name__)

SignalSource = Literal["supabase", "firestore", "none"]


class SignalStore:
    def __init__(self) -> None:
        self._supabase_enabled = (
            settings.supabase_enabled
            and bool(settings.supabase_project_url)
            and bool(settings.supabase_service_role_key)
        )
        self._firebase_enabled = settings.firebase_enabled

        self._supabase_url = settings.supabase_project_url
        self._supabase_key = settings.supabase_service_role_key
        self._supabase_table = settings.supabase_signal_table
        self._supabase_client: httpx.AsyncClient | None = None

        if self._supabase_enabled:
            self._supabase_client = httpx.AsyncClient(timeout=settings.supabase_timeout_seconds)
            logger.info("SignalStore using Supabase table=%s", self._supabase_table)

        self._firestore_db: firestore.Client | None = None
        if self._firebase_enabled:
            options: dict[str, Any] = {}
            if settings.firebase_project_id:
                options["projectId"] = settings.firebase_project_id
            app_name = "cerberus-strategy"
            try:
                app = firebase_admin.get_app(app_name)
            except ValueError:
                app = firebase_admin.initialize_app(options=options or None, name=app_name)
            self._firestore_db = firestore.client(app=app)
            logger.info("SignalStore using Firestore collection=%s", settings.firebase_signal_collection)

    async def list_recent(
        self,
        limit: int,
        source: Literal["auto", "supabase", "firestore"] = "auto",
    ) -> tuple[SignalSource, list[SignalRecord]]:
        if source in ("auto", "supabase"):
            records = await self._list_recent_supabase(limit)
            if records is not None:
                return ("supabase", records)
            if source == "supabase":
                return ("none", [])

        if source in ("auto", "firestore"):
            records = await self._list_recent_firestore(limit)
            if records is not None:
                return ("firestore", records)

        return ("none", [])

    async def _list_recent_supabase(self, limit: int) -> list[SignalRecord] | None:
        if (
            not self._supabase_enabled
            or self._supabase_client is None
            or not self._supabase_url
            or not self._supabase_key
        ):
            return None

        endpoint = f"{self._supabase_url.rstrip('/')}/rest/v1/{self._supabase_table}"
        try:
            resp = await self._supabase_client.get(
                endpoint,
                headers={
                    "apikey": self._supabase_key,
                    "Authorization": f"Bearer {self._supabase_key}",
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

    async def _list_recent_firestore(self, limit: int) -> list[SignalRecord] | None:
        if not self._firebase_enabled or self._firestore_db is None:
            return None

        return await asyncio.to_thread(self._list_recent_firestore_sync, limit)

    def _list_recent_firestore_sync(self, limit: int) -> list[SignalRecord]:
        assert self._firestore_db is not None
        query = (
            self._firestore_db.collection(settings.firebase_signal_collection)
            .order_by("created_at", direction=firestore.Query.DESCENDING)
            .limit(limit)
        )
        records: list[SignalRecord] = []
        for doc in query.stream():
            row = doc.to_dict()
            if not isinstance(row, dict):
                continue
            try:
                records.append(SignalRecord.model_validate(row))
            except Exception:
                continue
        return records

    async def aclose(self) -> None:
        if self._supabase_client is not None:
            await self._supabase_client.aclose()

    def status(self) -> dict[str, Any]:
        return {
            "supabase_enabled": self._supabase_enabled,
            "firebase_enabled": self._firebase_enabled,
            "supabase_table": self._supabase_table,
            "firebase_collection": settings.firebase_signal_collection,
        }
