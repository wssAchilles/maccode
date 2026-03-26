from __future__ import annotations

from typing import Any, Literal

import httpx
from firebase_admin import firestore

from app.config import settings
from app.schemas import SignalRecord

from .firestore_backend import build_firestore_client, list_recent_firestore
from .supabase_backend import build_supabase_client, list_recent_supabase, supabase_enabled

SignalSource = Literal["supabase", "firestore", "none"]


class SignalStore:
    def __init__(self) -> None:
        self._supabase_enabled = supabase_enabled()
        self._firebase_enabled = settings.firebase_enabled
        self._supabase_client: httpx.AsyncClient | None = build_supabase_client()
        self._firestore_db: firestore.Client | None = build_firestore_client()

    async def list_recent(
        self,
        limit: int,
        source: Literal["auto", "supabase", "firestore"] = "auto",
    ) -> tuple[SignalSource, list[SignalRecord]]:
        if source in ("auto", "supabase"):
            records = await list_recent_supabase(self._supabase_client, limit=limit)
            if records is not None:
                return ("supabase", records)
            if source == "supabase":
                return ("none", [])

        if source in ("auto", "firestore"):
            records = await list_recent_firestore(self._firestore_db, limit=limit)
            if records is not None:
                return ("firestore", records)

        return ("none", [])

    async def aclose(self) -> None:
        if self._supabase_client is not None:
            await self._supabase_client.aclose()

    def status(self) -> dict[str, Any]:
        return {
            "supabase_enabled": self._supabase_enabled,
            "firebase_enabled": self._firebase_enabled,
            "supabase_table": settings.supabase_signal_table,
            "firebase_collection": settings.firebase_signal_collection,
        }
