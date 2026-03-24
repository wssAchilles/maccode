from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

import firebase_admin
from firebase_admin import firestore

from app.config import settings
from app.schemas import Signal

logger = logging.getLogger(__name__)


class FirebaseSignalPublisher:
    def __init__(self) -> None:
        self.enabled = settings.firebase_enabled
        self._db: firestore.Client | None = None

        if not self.enabled:
            return

        options: dict[str, Any] = {}
        if settings.firebase_project_id:
            options["projectId"] = settings.firebase_project_id

        app_name = "cerberus-strategy"
        try:
            app = firebase_admin.get_app(app_name)
        except ValueError:
            app = firebase_admin.initialize_app(options=options or None, name=app_name)

        self._db = firestore.client(app=app)
        logger.info("Firebase publisher enabled for project=%s", settings.firebase_project_id)

    async def publish_signal(self, signal: Signal) -> None:
        if not self.enabled or self._db is None:
            return

        await asyncio.to_thread(self._write_signal, signal)

    def _write_signal(self, signal: Signal) -> None:
        assert self._db is not None
        doc_ref = self._db.collection(settings.firebase_signal_collection).document()
        doc_ref.set(
            {
                "strategy_id": signal.strategy_id,
                "symbol": signal.symbol,
                "signal": signal.signal,
                "confidence": signal.confidence,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )
