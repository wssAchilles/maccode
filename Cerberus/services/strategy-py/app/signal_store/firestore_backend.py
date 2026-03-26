from __future__ import annotations

import asyncio
import logging
from typing import Any

import firebase_admin
from firebase_admin import firestore

from app.config import settings
from app.schemas import SignalRecord

logger = logging.getLogger(__name__)


def build_firestore_client() -> firestore.Client | None:
    if not settings.firebase_enabled:
        return None

    options: dict[str, Any] = {}
    if settings.firebase_project_id:
        options["projectId"] = settings.firebase_project_id
    app_name = "cerberus-strategy"
    try:
        app = firebase_admin.get_app(app_name)
    except ValueError:
        app = firebase_admin.initialize_app(options=options or None, name=app_name)
    logger.info(
        "SignalStore using Firestore collection=%s",
        settings.firebase_signal_collection,
    )
    return firestore.client(app=app)


async def list_recent_firestore(
    db: firestore.Client | None,
    *,
    limit: int,
) -> list[SignalRecord] | None:
    if db is None:
        return None
    return await asyncio.to_thread(list_recent_firestore_sync, db, limit)


def list_recent_firestore_sync(
    db: firestore.Client,
    limit: int,
) -> list[SignalRecord]:
    query = (
        db.collection(settings.firebase_signal_collection)
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
