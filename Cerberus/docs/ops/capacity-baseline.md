# Capacity Baseline (Phase-Current)

## Baseline Context

- Sample date: `2026-03-25` (Asia/Shanghai)
- Environment: local single-node smoke baseline (`Redis + strategy + gateway`)
- Traffic shape: `120` sequential synthetic requests to `GET /api/v1/external/status` after `20` warmup requests
- Goal: provide a reproducible baseline for later Cloud Run scaling/cost tuning

## Measured Results

| Metric | Value |
|---|---:|
| sample request count | `120` |
| sample latency P95 | `0.81 ms` |
| sample latency average | `0.63 ms` |
| sample throughput | `1578.137 rps` |
| service-reported throughput (`/api/v1/metrics`) | `141.0 rps` |
| unit request cost (`UNIT_REQUEST_COST_USD`) | `0.0 USD` |
| estimated total cost (`/api/v1/metrics`) | `0.0 USD` |

## Interpretation

- This baseline is CPU/memory-local and does **not** represent internet-facing Cloud Run latency.
- Throughput in this run is bounded by loopback and process scheduling, not external dependencies.
- Unit cost is currently configured as `0`; production should set a non-zero baseline for cost governance.
- Service-side `http_latency_p95_ms` may report `0` for sub-millisecond paths due millisecond integer sampling.

## Reproduction Steps

1. Start local Redis + strategy + gateway.
2. Warm up endpoint with `20` requests.
3. Run `120` timed requests to `/api/v1/external/status`.
   - reusable gate script:
     - `GATEWAY_BASE_URL=http://127.0.0.1:8080 GATEWAY_PERF_REQUESTS=120 GATEWAY_PERF_MAX_P95_MS=2000 GATEWAY_PERF_MIN_RPS=1 GATEWAY_PERF_MAX_UNIT_COST_USD=1 python3 scripts/gateway_perf_gate.py`
4. Read `/api/v1/metrics` and record:
   - `http_latency_p95_ms`
   - `request_throughput_rps`
   - `estimated_request_cost_usd`
5. Read strategy `/metrics` and record stream policy gauges:
   - `cerberus_strategy_market_stream_legacy_pubsub_fallback_enabled`
   - `cerberus_strategy_event_stream_legacy_pubsub_publish_enabled`

## Next Calibration (Cloud Run)

- Repeat the same baseline in `staging` and `production` after deploy.
- Compare `sample_p95` vs service-reported `http_latency_p95_ms` to verify histogram/aggregation behavior.
- Use this document as the reference for horizontal scaling and queue/reclaim threshold tuning.
