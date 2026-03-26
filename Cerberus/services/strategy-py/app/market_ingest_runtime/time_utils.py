from __future__ import annotations

from datetime import datetime, timezone


def current_epoch_millis() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1_000)
