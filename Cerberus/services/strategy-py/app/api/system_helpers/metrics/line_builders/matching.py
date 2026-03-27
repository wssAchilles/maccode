from __future__ import annotations

from app.http import prometheus_escape

from ..context import MatchingMetricsContext


def matching_metrics_lines(context: MatchingMetricsContext) -> list[str]:
    stats = context.stats
    return [
        f"cerberus_strategy_matching_enabled {context.enabled}",
        f"cerberus_strategy_matching_reachable {context.reachable}",
        f"cerberus_strategy_matching_degraded {context.degraded}",
        (
            "cerberus_strategy_matching_status"
            f'{{status="{prometheus_escape(context.status)}"}} 1'
        ),
        f"cerberus_strategy_matching_uptime_seconds {context.uptime_seconds}",
        (
            "cerberus_strategy_matching_submit_order_latency_p95_ms "
            f"{float(stats.get('submit_order_latency_p95_ms', 0.0))}"
        ),
        (
            "cerberus_strategy_matching_submit_order_throughput_rps "
            f"{float(stats.get('submit_order_throughput_rps', 0.0))}"
        ),
        (
            "cerberus_strategy_matching_trade_throughput_rps "
            f"{float(stats.get('trade_throughput_rps', 0.0))}"
        ),
        (
            "cerberus_strategy_matching_inflight_requests "
            f"{int(stats.get('inflight_requests', 0))}"
        ),
        (
            "cerberus_strategy_matching_inflight_requests_peak "
            f"{int(stats.get('inflight_requests_peak', 0))}"
        ),
        (
            "cerberus_strategy_matching_max_inflight_requests "
            f"{int(stats.get('max_inflight_requests', 0))}"
        ),
        (
            "cerberus_strategy_matching_backpressure_waits_total "
            f"{int(stats.get('backpressure_waits_total', 0))}"
        ),
        (
            "cerberus_strategy_matching_backpressure_rejections_total "
            f"{int(stats.get('backpressure_rejections_total', 0))}"
        ),
        (
            "cerberus_strategy_matching_backpressure_wait_timeouts_total "
            f"{int(stats.get('backpressure_wait_timeouts_total', 0))}"
        ),
        (
            "cerberus_strategy_matching_backpressure_wait_ms_total "
            f"{int(stats.get('backpressure_wait_ms_total', 0))}"
        ),
    ]
