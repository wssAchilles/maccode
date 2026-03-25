# cerberus-strategy

Quant strategy service.

## Run

```bash
uv sync --project . --python ../../.venv/bin/python --active
uv run --project . uvicorn app.main:app --app-dir . --host 0.0.0.0 --port 8001
```

## Gurobi WLS

Set these env vars for cloud optimization:

- `GRB_LICENSEID`
- `GRB_WLSACCESSID`
- `GRB_WLSSECRET`

Optional Firebase signal persistence:

- `FIREBASE_ENABLED=true`
- `FIREBASE_PROJECT_ID=cerberus-9d94f`
- `FIREBASE_SIGNAL_COLLECTION=strategy_signals`

Optional Supabase signal persistence:

- `SUPABASE_ENABLED=true`
- `SUPABASE_PROJECT_URL=https://<project>.supabase.co`
- `SUPABASE_SERVICE_ROLE_KEY=<service-role-key>`
- `SUPABASE_SIGNAL_TABLE=strategy_signals`

Optional matching gRPC submit path (signal -> order):

- `MATCHING_ENABLED=true`
- `MATCHING_GRPC_TARGET=matching:50051`
- `MATCHING_GRPC_TARGET=https://<cloud-run-matching-url>` (Cloud Run TLS target supported)
- `STRATEGY_ACCOUNT_ID=default`
- `STRATEGY_ORDER_QUANTITY=0.001`
- `TRADE_EXECUTION_CHANNEL_PREFIX=trade.executions`
- `EXECUTION_RELAY_INTERVAL_SECONDS=1`
- `EXECUTION_RELAY_BATCH_LIMIT=100`

Market subscriptions:

- `MARKET_CHANNEL=md.orderbook.BTCUSDT` (single channel fallback)
- `MARKET_CHANNELS=md.orderbook.BTCUSDT,md.orderbook.ETHUSDT` (preferred multi-channel mode)

Signal smoke endpoint (works without Redis):

- `POST /api/v1/signal/ingest`

Runtime introspection endpoints:

- `GET /ready`
- `GET /metrics` (Prometheus)
- `GET /api/v1/signals/recent?limit=20&source=auto`
- `GET /api/v1/status/persistence`

Matching control endpoints:

- `POST /api/v1/matching/orders`
- `POST /api/v1/matching/orders/{order_id}/cancel`
- `GET /api/v1/matching/orders/{order_id}`
- `GET /api/v1/matching/executions`
- `GET /api/v1/matching/health`
- `GET /api/v1/matching/stats`
- `GET /api/v1/matching/orderbook?symbol=BTCUSDT&depth=10`

Observability notes:

- Strategy gRPC client attaches `x-request-id` metadata to matching RPC calls.
- Strategy HTTP middleware preserves incoming `x-request-id` (or generates one) and echoes it in response headers.
- HTTP errors are wrapped as `{ "error": { "code", "message", "request_id" } }`.
- `/api/v1/status/persistence` now includes `matching.health` and `matching.stats`.
- `/metrics` exposes Prometheus counters/gauges for worker loops, signal throughput, storage toggles, and matching reachability.
