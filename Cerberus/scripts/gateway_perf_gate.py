#!/usr/bin/env python3
"""Gateway deploy/perf gate utility.

Runs sequential probes against gateway health/status path and validates
latency/throughput/unit-cost gates using gateway `/api/v1/metrics`.
"""

from __future__ import annotations

import json
import os
import statistics
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass


@dataclass(frozen=True)
class GateConfig:
    base_url: str
    samples: int
    max_p95_ms: float
    min_rps: float
    max_unit_cost_usd: float
    request_timeout_seconds: float
    status_path: str
    metrics_path: str
    request_id_prefix: str


def _env_text(key: str, default: str) -> str:
    value = os.getenv(key, default).strip()
    return value if value else default


def load_config_from_env() -> GateConfig:
    base_url = _env_text("GATEWAY_BASE_URL", "").rstrip("/")
    if not base_url:
        raise SystemExit("GATEWAY_BASE_URL is required")
    samples = max(int(_env_text("GATEWAY_PERF_REQUESTS", "40")), 1)
    max_p95_ms = float(_env_text("GATEWAY_PERF_MAX_P95_MS", "800"))
    min_rps = float(_env_text("GATEWAY_PERF_MIN_RPS", "2"))
    max_unit_cost_usd = float(_env_text("GATEWAY_PERF_MAX_UNIT_COST_USD", "0.01"))
    request_timeout_seconds = float(_env_text("GATEWAY_PERF_TIMEOUT_SECONDS", "15"))
    status_path = _normalize_path(_env_text("GATEWAY_PERF_STATUS_PATH", "/api/v1/external/status"))
    metrics_path = _normalize_path(_env_text("GATEWAY_PERF_METRICS_PATH", "/api/v1/metrics"))
    request_id_prefix = _env_text("GATEWAY_PERF_REQUEST_ID_PREFIX", "deploy-gate")
    return GateConfig(
        base_url=base_url,
        samples=samples,
        max_p95_ms=max_p95_ms,
        min_rps=min_rps,
        max_unit_cost_usd=max_unit_cost_usd,
        request_timeout_seconds=request_timeout_seconds,
        status_path=status_path,
        metrics_path=metrics_path,
        request_id_prefix=request_id_prefix,
    )


def _normalize_path(path: str) -> str:
    return path if path.startswith("/") else f"/{path}"


def get_json(url: str, timeout_seconds: float, request_id: str | None = None) -> dict:
    req = urllib.request.Request(url=url, method="GET")
    if request_id:
        req.add_header("x-request-id", request_id)
    with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
        body = resp.read().decode("utf-8")
        return json.loads(body)


def _percentile_95(samples_ms: list[float]) -> float:
    ordered = sorted(samples_ms)
    index = max(int(round(0.95 * len(ordered) + 0.5)) - 1, 0)
    return ordered[min(index, len(ordered) - 1)]


def run_gate(config: GateConfig) -> dict[str, float | int]:
    latencies_ms: list[float] = []

    started_at = time.perf_counter()
    for idx in range(config.samples):
        request_id = f"{config.request_id_prefix}-{idx}"
        call_started = time.perf_counter()
        try:
            payload = get_json(
                f"{config.base_url}{config.status_path}",
                timeout_seconds=config.request_timeout_seconds,
                request_id=request_id,
            )
        except urllib.error.HTTPError as exc:
            raise SystemExit(f"{config.status_path} failed: {exc}") from exc
        if payload.get("error") not in (None, {}):
            raise SystemExit(f"{config.status_path} returned error envelope: {payload}")
        latencies_ms.append((time.perf_counter() - call_started) * 1000.0)

    elapsed = max(time.perf_counter() - started_at, 1e-6)
    throughput_rps = config.samples / elapsed
    p95_ms = _percentile_95(latencies_ms)
    mean_ms = statistics.mean(latencies_ms)

    metrics = get_json(
        f"{config.base_url}{config.metrics_path}",
        timeout_seconds=config.request_timeout_seconds,
        request_id=f"{config.request_id_prefix}-metrics",
    )
    metrics_data = metrics.get("data", {}) if isinstance(metrics, dict) else {}
    unit_cost = float(metrics_data.get("estimated_request_cost_usd", 0.0) or 0.0)
    service_p95 = float(metrics_data.get("http_latency_p95_ms", 0.0) or 0.0)

    summary = {
        "samples": config.samples,
        "sample_p95_ms": round(p95_ms, 2),
        "sample_mean_ms": round(mean_ms, 2),
        "sample_throughput_rps": round(throughput_rps, 3),
        "service_reported_p95_ms": round(service_p95, 2),
        "unit_request_cost_usd": unit_cost,
    }
    print(json.dumps(summary, ensure_ascii=False))

    if p95_ms > config.max_p95_ms:
        raise SystemExit(f"backend p95 gate failed: {p95_ms:.2f}ms > {config.max_p95_ms}ms")
    if throughput_rps < config.min_rps:
        raise SystemExit(
            f"backend throughput gate failed: {throughput_rps:.3f}rps < {config.min_rps}rps"
        )
    if unit_cost > config.max_unit_cost_usd:
        raise SystemExit(
            "backend unit cost gate failed: "
            f"{unit_cost:.8f} > {config.max_unit_cost_usd:.8f}"
        )

    return summary


def main() -> int:
    config = load_config_from_env()
    run_gate(config)
    return 0


if __name__ == "__main__":
    sys.exit(main())
