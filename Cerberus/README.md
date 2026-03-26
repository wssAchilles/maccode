# Cerberus v1

Industrial event-driven microservices skeleton for quant trading and high-frequency matching.

## Architecture

- External: `React -> Rust Gateway` via REST + WebSocket.
- Internal: service contracts in `proto/` with gRPC + Protobuf.
- Async event bus: Redis Streams (consumer group primary) + Redis Pub/Sub (legacy fallback).
- Services:
  - `apps/frontend`: React + TypeScript + Zustand + Lightweight Charts + Firebase SDK bootstrap.
  - `services/gateway-rs`: Rust Axum gateway, Binance stream ingestion, Redis publishing, REST/WS APIs.
    - Startup/bootstrap skeleton:
      - `bootstrap/config.rs` for environment loading + runtime policy validation.
      - `bootstrap/router.rs` for route composition and middleware/cors assembly.
      - `main.rs` kept as lifecycle orchestration only.
    - Order ingest skeleton:
      - `ingest/orders.rs` for ingest orchestrator.
      - `ingest/orders/stream.rs` for Redis Stream consumer-group ingest/reclaim/poison path.
      - `ingest/orders/stream/stream_group.rs` for consumer-group bootstrap + pending replay.
      - `ingest/orders/stream/{stream_io,stream_payload,stream_processing,stream_reclaim}.rs` for stream read/parse/process/reclaim units.
      - `ingest/orders/pubsub.rs` for legacy Pub/Sub fallback.
      - `ingest/orders/stream_metrics.rs` for stream ingest metrics state transitions.
    - Strategy upstream skeleton:
      - `handlers/trading/strategy/upstream.rs` for request orchestration.
      - `handlers/trading/strategy/upstream/{error,queue,circuit,metrics}.rs` for upstream runtime concerns.
- `services/strategy-py`: FastAPI quant service + Gurobi mean-variance optimization endpoint.
  - Optional Firebase Firestore signal persistence.
  - Runtime skeleton:
    - `runtime_container.py` for dependency assembly.
    - `signal_service.py` / `summary_service.py` / `matching_service.py` for API-facing application services.
    - `system_status_service.py` for ready/metrics/persistence application service.
    - `signal_engine_service.py` for per-symbol signal engine orchestration.
    - `worker_idempotency.py` for idempotency ownership.
    - `worker_lifecycle.py` for worker start/stop/supervisor lifecycle.
    - `market_ingest_runtime/` package for market ingest orchestration:
      - `loop.py` / `pubsub_runtime.py` / `stream_runtime.py`
      - `stream_io.py` / `stream_processing.py` / `stream_reclaim.py`
      - `retry.py` / `time_utils.py`
    - `event_runtime.py` for event publish/relay orchestration.
- `services/matching-cpp`: C++20 matching core + order service layer (execution journal, snapshot/stats) + GTest.
  - gRPC build path enabled when `gRPC + Protobuf` dependencies are present.
- Infra:
  - Local: Docker Compose (`redis`, `postgres`, `timescaledb`, all app services).
  - Cloud: Firebase Hosting (frontend) + Cloud Run (gateway/strategy) + Upstash Redis + Supabase Postgres, provisioned by Terraform under `infra/terraform`.
  - Cloud Run runtime capacity profiles are Terraform-managed per service (`cloud_run_gateway`, `cloud_run_strategy`, `cloud_run_matching`).

## APIs (v1)

- Gateway external endpoints:
  - `GET /ready`
  - `GET /metrics` (Prometheus)
  - `GET /api/v1/klines`
  - `GET /api/v1/orderbook/snapshot?symbol=BTCUSDT`
  - `GET /api/v1/metrics`
  - `GET /api/v1/orders/events/recent` (supports `limit`,`channel`,`account_id`,`symbol`,`order_id`,`status`,`request_id`)
  - `GET /api/v1/external/status`
  - `GET /api/v1/strategy/summary`
  - `GET /api/v1/trading/policy`
  - `GET /api/v1/binance/symbol-rules`
  - `POST /api/v1/binance/order/test`
  - `GET /api/v1/alpaca/account`
  - `POST /api/v1/alpaca/orders`
  - `POST /api/v1/alpaca/orders/{order_id}/cancel`
  - `WS /ws/market`
- `WS /ws/orders`
    - streams structured order events from Redis channels (default: `strategy.signals.default`, `trade.executions.default`)
    - also emits gateway-generated execution events for Binance test order / Alpaca submit / Alpaca cancel
    - each message includes `channel`, `payload`, `received_at`
    - execution payloads use canonical keys: `event`, `provider`, `account_id`, `order_id`, `symbol`, `status`, `request_id`
- Strategy endpoint:
  - `GET /ready`
  - `GET /metrics` (Prometheus)
  - `POST /api/v1/optimize/mean-variance`
  - `GET /api/v1/signal`
  - `GET /api/v1/signals/recent`
  - `GET /api/v1/status/persistence`
  - `GET /api/v1/summary` (internal aggregate endpoint used by Gateway with fallback)
  - `POST /api/v1/signal/ingest`
  - `POST /api/v1/matching/orders`
  - `POST /api/v1/matching/orders/{order_id}/cancel`
  - `GET /api/v1/matching/orders/{order_id}`
  - `GET /api/v1/matching/executions` (supports `account_id`, optional `symbol`,`order_id`,`request_id`)
  - `GET /api/v1/matching/health`
  - `GET /api/v1/matching/stats`
  - `GET /api/v1/matching/orderbook?symbol=BTCUSDT&depth=10`

Request tracing and error model:

- Gateway and Strategy both support `x-request-id` propagation (echoed in response headers).
- Gateway supports `idempotency-key` / `x-idempotency-key` on mutating APIs and echoes normalized value.
- Gateway upstream probe (`/api/v1/external/status`) forwards `x-request-id` to Strategy health checks.
- Gateway REST payloads are unified as `{ "request_id", "data", "error" }` where `error` is `null` on success.
- Trading success payloads on core execution APIs also include `request_id` for frontend flow traceability.

Local contract smoke:

- `./scripts/smoke_local.sh` validates `/health`, `/ready`, `/metrics`, `x-request-id` propagation, and unified error envelope.

Frontend runtime envs:

- `VITE_GATEWAY_BASE`
- `VITE_STRATEGY_BASE`
- `VITE_AUTH_REQUIRED`
- `VITE_FIREBASE_API_KEY`
- `VITE_FIREBASE_AUTH_DOMAIN`
- `VITE_FIREBASE_PROJECT_ID`
- `VITE_FIREBASE_STORAGE_BUCKET`
- `VITE_FIREBASE_MESSAGING_SENDER_ID`
- `VITE_FIREBASE_APP_ID`
- `VITE_DISABLE_LIVE_STREAM` (`true` for deterministic test/e2e mode)

Firebase Authentication behavior:

- Login page only provides email and Google sign-in.
- No explicit register button.
- Email sign-in runs `login -> auto-register fallback` for first-time accounts.
- Google sign-in uses Firebase onboarding (first login auto-creates account).

## Quickstart

1. Sync Python dependencies into existing `.venv`:

```bash
source .venv/bin/activate
uv lock --project services/strategy-py
uv sync --project services/strategy-py --python .venv/bin/python --active --frozen --all-groups
```

Run strategy tests:

```bash
source .venv/bin/activate
uv run --project services/strategy-py --active pytest services/strategy-py/tests
```

2. Install frontend dependencies:

```bash
cd apps/frontend && npm install && cd ../..
```

Frontend quality gates:

```bash
cd apps/frontend
npm run test
npm run build
npm run check:bundle-budget
npm run test:e2e
npm run lighthouse
```

Deployed release gate (against online URL):

```bash
cd apps/frontend
E2E_BASE_URL="https://<your-hosting-url>" E2E_GATE_MODE=true E2E_USE_DEPLOYED=true E2E_AUTH_EMAIL="gate-user@example.com" E2E_AUTH_PASSWORD="replace_me" npm run test:e2e:gate
LHCI_COLLECT_URL="https://<your-hosting-url>" npm run lighthouse:gate
```

`npm run lighthouse:gate` runs both desktop and mobile SLO assertions.
Note: Lighthouse navigation runs may not always emit INP (`auditRan=0`), so INP is treated as warning in gate; responsiveness hard gate uses `total-blocking-time`.

3. Start local stack:

```bash
docker compose up -d --build
```

Prometheus (local Compose) is available at:

- [http://localhost:9090](http://localhost:9090)

4. Open frontend:

- [http://localhost:5173](http://localhost:5173)

5. Bootstrap GCP project APIs:

```bash
./scripts/bootstrap_gcp.sh cerberus-9d94f asia-east2
```

6. Run non-container smoke test:

```bash
make smoke
```

7. Bootstrap Supabase signal table (optional):

```bash
export SUPABASE_DB_URL=postgresql://...
uv run --with "psycopg[binary]" scripts/bootstrap_supabase_signals.py
```

8. Sync exchange secrets + deploy gateway from source:

```bash
export BINANCE_API_KEY=...
export BINANCE_API_SECRET=...
export ALPACA_API_KEY=...
export ALPACA_API_SECRET=...
./scripts/sync_gcp_exchange_secrets.sh cerberus-9d94f asia-east2
./scripts/deploy_gateway_source.sh cerberus-9d94f asia-east2
./scripts/deploy_strategy_source.sh cerberus-9d94f asia-east2
```

For faster repeat gateway releases, use cached image deploy:

```bash
./scripts/deploy_gateway_cached.sh cerberus-9d94f asia-east2
```

## Gurobi + Firebase Secrets

- Do not commit secrets in source control.
- Use `deploy/compose/.env.example` as template for local runtime variables.
- For GCP deployment, use Secret Manager values and map them to runtime env vars.

Important: if any Gurobi WLS credential has been exposed in chat/screenshots, rotate it immediately in the Gurobi portal and update Secret Manager.

## Cloud Secret Mapping (GCP)

- `cerberus-dev-upstash-redis-url` -> `REDIS_URL` (`rediss://...`, TLS required)
- `cerberus-dev-upstash-redis-rest-url` -> `UPSTASH_REDIS_REST_URL`
- `cerberus-dev-upstash-redis-rest-token` -> `UPSTASH_REDIS_REST_TOKEN`
- `cerberus-dev-supabase-project-url` -> `SUPABASE_PROJECT_URL`
- `cerberus-dev-supabase-anon-key` -> `SUPABASE_ANON_KEY`
- `cerberus-dev-supabase-service-role-key` -> `SUPABASE_SERVICE_ROLE_KEY`
- `cerberus-dev-supabase-db-url` -> `SUPABASE_DB_URL`
- `cerberus-dev-gurobi-licenseid` -> `GRB_LICENSEID`
- `cerberus-dev-gurobi-wlsaccessid` -> `GRB_WLSACCESSID`
- `cerberus-dev-gurobi-wlssecret` -> `GRB_WLSSECRET`
- `cerberus-dev-firebase-web-api-key` -> `FIREBASE_WEB_API_KEY`
- `cerberus-dev-jwt-hs256-secret` -> `JWT_HS256_SECRET`
- `cerberus-dev-binance-api-key` -> `BINANCE_API_KEY`
- `cerberus-dev-binance-api-secret` -> `BINANCE_API_SECRET`
- `cerberus-dev-alpaca-api-key` -> `ALPACA_API_KEY`
- `cerberus-dev-alpaca-api-secret` -> `ALPACA_API_SECRET`

Gateway stream envs:

- `REDIS_ORDERBOOK_CHANNEL` (market fanout channel)
- `REDIS_ORDERBOOK_CHANNEL_PREFIX` (per-symbol market channel prefix, default `md.orderbook`)
- `REDIS_TICK_CHANNEL_PREFIX` (per-symbol tick channel prefix, default `md.ticks`)
- `REDIS_MARKET_EVENTS_STREAM_ENABLED` / `REDIS_MARKET_EVENTS_STREAM_KEY` / `REDIS_MARKET_EVENTS_STREAM_MAXLEN`
- `REDIS_MARKET_EVENTS_PUBLISH_LEGACY_PUBSUB` (stream-only or dual-write with legacy pubsub)
- `MARKET_SYMBOLS` (comma-separated Binance symbols, e.g. `BTCUSDT,ETHUSDT`)
- `MARKET_WS_URL` (optional explicit market WS URL; for Binance Futures stream use `wss://fstream.binance.com/stream?streams=btcusdt@bookTicker/ethusdt@bookTicker`)
- `KLINE_API_URL` (optional explicit kline URL; for Binance Futures test path use `https://demo-fapi.binance.com/fapi/v1/klines`)
- `REDIS_ORDER_EVENTS_CHANNELS` (comma-separated order-event channels for `/ws/orders`)
- `REDIS_ORDER_EVENTS_STREAM_ENABLED` / `REDIS_ORDER_EVENTS_STREAM_KEY` / `REDIS_ORDER_EVENTS_CONSUMER_GROUP` / `REDIS_ORDER_EVENTS_CONSUMER_NAME`
- `REDIS_ORDER_EVENTS_LEGACY_PUBSUB_FALLBACK` (allow stream ingest downgrade to legacy Pub/Sub on failure; set `false` for strict stream-first mode)
- `REDIS_ORDER_EVENTS_READ_BATCH_SIZE` / `REDIS_ORDER_EVENTS_READ_BLOCK_MS` / `REDIS_ORDER_EVENTS_PENDING_REPLAY_COUNT` / `REDIS_ORDER_EVENTS_BATCH_WINDOW_MS`
- `REDIS_ORDER_EVENTS_MAX_RETRIES_BEFORE_FALLBACK` / `REDIS_ORDER_EVENTS_RETRY_BACKOFF_MS` / `REDIS_ORDER_EVENTS_RETRY_BACKOFF_MAX_MS`
- `REDIS_ORDER_EVENTS_RECLAIM_ENABLED` / `REDIS_ORDER_EVENTS_RECLAIM_INTERVAL_MS` / `REDIS_ORDER_EVENTS_RECLAIM_IDLE_MS` / `REDIS_ORDER_EVENTS_RECLAIM_BATCH_SIZE`
- `REDIS_ORDER_EVENTS_MAX_DELIVERY_ATTEMPTS` / `REDIS_ORDER_EVENTS_POISON_STREAM_KEY` / `REDIS_ORDER_EVENTS_POISON_STREAM_MAXLEN`
- `REDIS_ORDER_EVENTS_PENDING_WARN_THRESHOLD` / `REDIS_ORDER_EVENTS_LAG_WARN_THRESHOLD`
- `STRATEGY_SUMMARY_CACHE_TTL_MS` (gateway side short-lived cache for `/api/v1/strategy/summary`)
- `STRATEGY_SUMMARY_BATCH_WINDOW_MS` (gateway single-flight coalescing window before upstream summary fetch)
- `READY_MAX_MARKET_STALENESS_MS` (optional ready gate; `0` disables market freshness checks)
- `UNIT_REQUEST_COST_USD` (cost baseline used by gateway `/metrics` + `/api/v1/metrics`)
- `JWT_AUTH_ENABLED` / `JWT_AUTH_REQUIRE_IN_PRODUCTION` / `JWT_HS256_SECRET` / `JWT_ISSUER` / `JWT_AUDIENCE`
- `BINANCE_API_KEY` / `BINANCE_API_SECRET` (signed Binance REST)
- `BINANCE_ORDER_TEST_PATH` (defaults to `/api/v3/order/test`; use `/fapi/v1/order/test` for Futures API)
- `ALPACA_API_KEY` / `ALPACA_API_SECRET` / `ALPACA_TRADING_BASE_URL`
- `STRATEGY_BASE_URL` (optional strategy upstream probe for gateway `/api/v1/external/status`)
- `STRATEGY_INTERNAL_AUTH_ENABLED` / `STRATEGY_INTERNAL_AUTH_AUDIENCE` / `STRATEGY_INTERNAL_AUTH_TOKEN_TTL_SECONDS`
- `GCP_METADATA_IDENTITY_URL` (override metadata identity endpoint when needed)
- `STRATEGY_UPSTREAM_TIMEOUT_MS` / `STRATEGY_UPSTREAM_HEALTH_TIMEOUT_MS`
- `STRATEGY_UPSTREAM_MAX_INFLIGHT` / `STRATEGY_UPSTREAM_QUEUE_TIMEOUT_MS`
- `STRATEGY_UPSTREAM_CIRCUIT_ENABLED` / `STRATEGY_UPSTREAM_CIRCUIT_FAILURE_THRESHOLD` / `STRATEGY_UPSTREAM_CIRCUIT_OPEN_MS`
- `TRADING_POLICY_ENFORCED` (server-side risk gate)
- `BINANCE_ALLOWED_SYMBOLS` / `ALPACA_ALLOWED_SYMBOLS`
- `MAX_BINANCE_ORDER_QTY` / `MAX_BINANCE_ORDER_NOTIONAL_USD`
- `MAX_ALPACA_ORDER_QTY` / `MAX_ALPACA_LIMIT_NOTIONAL_USD`
- `MATCHING_SUBMIT_LATENCY_WINDOW_SIZE` (rolling sample size for matching submit P95)
- `MATCHING_MAX_INFLIGHT_REQUESTS` / `MATCHING_INFLIGHT_ACQUIRE_TIMEOUT_MS` (matching backpressure budget/queue wait)
- `MATCHING_GRPC_MAX_POLLERS` / `MATCHING_GRPC_MIN_POLLERS` / `MATCHING_GRPC_NUM_CQS`

Gateway external trading endpoints:

- `POST /api/v1/binance/order/test` (signed test endpoint, does not place real order)
- `GET /api/v1/alpaca/account`
- `POST /api/v1/alpaca/orders`

Signal persistence path:

- Ingest (Gateway/Manual) -> Strategy -> Firestore + Supabase `strategy_signals`
- Matching execution relay (Strategy) -> Redis `trade.executions.<account_id>` -> Gateway `/ws/orders`
- Strategy emits canonical stream events to `EVENT_STREAM_KEY` with envelope:
  - `event_type`, `event_id`, `created_at`, `schema_version`, `payload` (+ optional `correlation_id`)
- Strategy idempotency can use Redis-backed claims:
  - `IDEMPOTENCY_STORE_REDIS_ENABLED`, `IDEMPOTENCY_REDIS_KEY_PREFIX`, `SIGNAL_IDEMPOTENCY_TTL_SECONDS`
- Strategy market ingest can use Redis Stream consumer group:
  - `MARKET_STREAM_ENABLED`, `MARKET_STREAM_KEY`, `MARKET_STREAM_CONSUMER_GROUP`, `MARKET_STREAM_LEGACY_PUBSUB_FALLBACK`
  - `MARKET_STREAM_RECLAIM_ENABLED`, `MARKET_STREAM_RECLAIM_INTERVAL_MS`, `MARKET_STREAM_RECLAIM_IDLE_MS`, `MARKET_STREAM_RECLAIM_BATCH_SIZE`
  - `MARKET_STREAM_MAX_DELIVERY_ATTEMPTS`, `MARKET_STREAM_POISON_STREAM_KEY`, `MARKET_STREAM_POISON_STREAM_MAXLEN`
  - `MARKET_STREAM_PENDING_WARN_THRESHOLD`, `MARKET_STREAM_LAG_WARN_THRESHOLD`
- Matching gRPC schema fallback can be pinned with:
  - `CERBERUS_EVENT_SCHEMA_VERSION` (default `v1`)

Matching service runtime capabilities:

- Price-time priority matching core
- Order lifecycle tracking (`NEW/PARTIALLY_FILLED/FILLED/CANCELED/REJECTED`)
- Execution journal with per-account query helpers
- gRPC `OrderService` implementation (submit/cancel/get/stream) when built with gRPC deps
- gRPC health/stats endpoints for service observability (`Health`, `GetServiceStats`)
- Matching degraded signals are explicit:
  - `Health.status=degraded:*`
  - gRPC trailing metadata `x-cerberus-degraded` / `x-cerberus-degraded-reason`
- Matching `GetServiceStats` now includes capacity baselines:
  - `submit_order_requests_total`, `submit_order_errors_total`, `submit_order_rejections_total`
  - `submit_order_latency_p95_ms`, `submit_order_throughput_rps`, `trade_throughput_rps`
  - `inflight_requests`, `inflight_requests_peak`, `max_inflight_requests`
  - `backpressure_waits_total`, `backpressure_rejections_total`, `backpressure_wait_timeouts_total`, `backpressure_wait_ms_total`
  - runtime knobs echo: `execution_stream_limit`, `submit_latency_window_size`, `grpc_min_pollers`, `grpc_max_pollers`, `grpc_num_cqs`
- Non-gRPC fallback binary startup is disabled by default (`MATCHING_ALLOW_STUB_STARTUP=true` enables diagnostic warmup only).
- Local gRPC build command: `cmake -S services/matching-cpp -B services/matching-cpp/build-grpc -DENABLE_GRPC_SERVICE=ON`

OrderService RPC set:

- `SubmitOrder`
- `CancelOrder`
- `GetOrder`
- `GetOrderBook`
- `StreamExecutions`
- `Health`
- `GetServiceStats`

Proto workflow:

- Source contracts live under `proto/cerberus/*/v1`.
- Run `buf lint && buf generate` to produce:
  - Python: `services/strategy-py/app/gen`
  - C++: `services/matching-cpp/gen`
  - Rust: `services/gateway-rs/src/gen`
  - TS: `apps/frontend/src/gen`

## GCP Project Defaults

- Project: `cerberus-9d94f`
- Region: `asia-east2`
- Environment: `dev` only

## CI/CD

GitHub Actions workflow at `.github/workflows/ci.yml` runs:

- Terraform infra checks (`fmt`, `init -backend=false`, `validate`)
- Python tests (strategy)
- Rust `cargo check` (gateway)
- C++ build and tests (matching)
- Frontend unit tests + Playwright e2e + build + Lighthouse assertions
- Optional Buf checks (when `buf` is available in runner)

Cloud deployment workflow is `.github/workflows/deploy.yml`:

- Builds and deploys `gateway-rs` + `strategy-py` to Cloud Run.
- Builds frontend and deploys to Firebase Hosting.
- Runs deployed e2e/lighthouse gate against the live Firebase URL.
- Runs backend deploy gate with latency/throughput/unit-cost thresholds against deployed gateway.
- Requires GitHub secrets `FIREBASE_E2E_EMAIL` and `FIREBASE_E2E_PASSWORD` for auth-enabled gate runs.
- Requires exchange secrets `BINANCE_API_KEY`, `BINANCE_API_SECRET`, `ALPACA_API_KEY`, `ALPACA_API_SECRET` for trading endpoints.
- Requires `JWT_HS256_SECRET` and runs `scripts/validate_deploy_policy.sh` as deploy gate.

Operational references:

- `docs/ops/runbook-stream-reliability.md`
- `docs/ops/alerts-and-slo.md`
- `docs/ops/capacity-baseline.md`

## Post-Deploy Chrome DevTools MCP Gate (Manual Release Blocker)

Use deployed Firebase Hosting URL as the single acceptance entry:

1. Open the online site in desktop viewport and verify:
   - market cards update
   - precheck -> submit -> response for Binance test order
   - Alpaca submit + cancel path closes loop
   - matching orderbook panel and execution timeline stay linked
2. Repeat in mobile viewport (usability verification, not equal density).
3. Check console:
   - any `error` level log => release blocked
4. Check network:
   - core APIs (`/api/v1/strategy/summary`, `/api/v1/klines`, `/api/v1/binance/symbol-rules`, `/api/v1/trading/policy`, `/api/v1/binance/order/test`, `/api/v1/alpaca/orders`) must not return `4xx/5xx`
5. Performance SLO:
   - LCP <= 2.0s
   - INP <= 150ms (measured by interaction trace / field probe)
   - CLS < 0.1
