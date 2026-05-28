from __future__ import annotations

from typing import Any

from scripts.generate_demo_report import generate_demo_report


class StatsService:
    def get_realtime_report(self) -> dict[str, Any]:
        return generate_demo_report()
