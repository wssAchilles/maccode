from __future__ import annotations

from typing import Any

from application.services.runtime_state import DemoRuntime


class StatsService:
    def __init__(self, runtime: DemoRuntime) -> None:
        self.runtime = runtime

    def get_realtime_report(self) -> dict[str, Any]:
        return self.runtime.get_realtime_report()

    def get_history(self, limit: int = 100) -> list[dict[str, Any]]:
        return self.runtime.get_history(limit=limit)

    def get_cumulative_stats(self) -> dict[str, Any]:
        return self.runtime.get_cumulative_stats()
