from __future__ import annotations

from typing import Any

from app.config import settings
from app.http import prometheus_escape


def base_metrics_lines(uptime_seconds: int) -> list[str]:
    return [
        "# HELP cerberus_strategy_up Strategy process health.",
        "# TYPE cerberus_strategy_up gauge",
        "cerberus_strategy_up 1",
        (
            "cerberus_strategy_build_info"
            f'{{service="{prometheus_escape(settings.service_name)}",'
            f'version="{prometheus_escape(settings.service_version)}"}} 1'
        ),
        f"cerberus_strategy_uptime_seconds {uptime_seconds}",
    ]


def stores_metrics_lines(stores: dict[str, Any]) -> list[str]:
    return [
        f"cerberus_strategy_store_enabled{{store=\"firebase\"}} {1 if stores['firebase_enabled'] else 0}",
        f"cerberus_strategy_store_enabled{{store=\"supabase\"}} {1 if stores['supabase_enabled'] else 0}",
    ]
