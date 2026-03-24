# Cerberus v1

Industrial event-driven microservices skeleton for quant trading and high-frequency matching.

## Architecture

- External: `React -> Rust Gateway` via REST + WebSocket.
- Internal: service contracts in `proto/` with gRPC + Protobuf.
- Async market bus: Redis Pub/Sub.
- Services:
  - `apps/frontend`: React + TypeScript + Zustand + Lightweight Charts + Firebase SDK bootstrap.
  - `services/gateway-rs`: Rust Axum gateway, Binance stream ingestion, Redis publishing, REST/WS APIs.
- `services/strategy-py`: FastAPI quant service + Gurobi mean-variance optimization endpoint.
  - Optional Firebase Firestore signal persistence.
- `services/matching-cpp`: C++20 matching core + order service layer (execution journal, snapshot/stats) + GTest.
  - gRPC build path enabled when `gRPC + Protobuf` dependencies are present.
- Infra:
  - Local: Docker Compose (`redis`, `postgres`, `timescaledb`, all app services).
  - Cloud: Terraform templates under `infra/terraform`.

## APIs (v1)

- Gateway external endpoints:
  - `GET /ready`
  - `GET /metrics` (Prometheus)
  - `GET /api/v1/klines`
  - `GET /api/v1/orderbook/snapshot?symbol=BTCUSDT`
  - `GET /api/v1/metrics`
  - `GET /api/v1/orders/events/recent`
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
- Strategy endpoint:
  - `GET /ready`
  - `GET /metrics` (Prometheus)
  - `POST /api/v1/optimize/mean-variance`
  - `GET /api/v1/signal`
  - `GET /api/v1/signals/recent`
  - `GET /api/v1/status/persistence`
  - `POST /api/v1/signal/ingest`
  - `POST /api/v1/matching/orders`
  - `POST /api/v1/matching/orders/{order_id}/cancel`
  - `GET /api/v1/matching/orders/{order_id}`
  - `GET /api/v1/matching/executions` (supports `account_id`, optional `symbol`)
  - `GET /api/v1/matching/health`
  - `GET /api/v1/matching/stats`
  - `GET /api/v1/matching/orderbook?symbol=BTCUSDT&depth=10`

Request tracing and error model:

- Gateway and Strategy both support `x-request-id` propagation (echoed in response headers).
- Gateway upstream probe (`/api/v1/external/status`) forwards `x-request-id` to Strategy health checks.
- Error payloads follow `{ "error": { "code", "message", "request_id" } }` on wrapped endpoints.

Local contract smoke:

- `./scripts/smoke_local.sh` validates `/health`, `/ready`, `/metrics`, `x-request-id` propagation, and unified error envelope.

Frontend runtime envs:

- `VITE_GATEWAY_BASE`
- `VITE_STRATEGY_BASE`
- `VITE_DISABLE_LIVE_STREAM` (`true` for deterministic test/e2e mode)

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
npm run test:e2e
npm run lighthouse
```

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

- `cerberus-upstash-redis-url` -> `REDIS_URL` (`rediss://...`, TLS required)
- `cerberus-upstash-redis-rest-url` -> `UPSTASH_REDIS_REST_URL`
- `cerberus-upstash-redis-rest-token` -> `UPSTASH_REDIS_REST_TOKEN`
- `cerberus-supabase-project-url` -> `SUPABASE_PROJECT_URL`
- `cerberus-supabase-anon-key` -> `SUPABASE_ANON_KEY`
- `cerberus-supabase-service-role-key` -> `SUPABASE_SERVICE_ROLE_KEY`
- `cerberus-supabase-db-url` -> `SUPABASE_DB_URL`
- `cerberus-grb-licenseid` -> `GRB_LICENSEID`
- `cerberus-grb-wlsaccessid` -> `GRB_WLSACCESSID`
- `cerberus-grb-wlssecret` -> `GRB_WLSSECRET`

Gateway stream envs:

- `REDIS_ORDERBOOK_CHANNEL` (market fanout channel)
- `REDIS_ORDERBOOK_CHANNEL_PREFIX` (per-symbol market channel prefix, default `md.orderbook`)
- `REDIS_TICK_CHANNEL_PREFIX` (per-symbol tick channel prefix, default `md.ticks`)
- `MARKET_SYMBOLS` (comma-separated Binance symbols, e.g. `BTCUSDT,ETHUSDT`)
- `MARKET_WS_URL` (optional explicit market WS URL; for Binance Futures stream use `wss://fstream.binance.com/stream?streams=btcusdt@bookTicker/ethusdt@bookTicker`)
- `KLINE_API_URL` (optional explicit kline URL; for Binance Futures test path use `https://demo-fapi.binance.com/fapi/v1/klines`)
- `REDIS_ORDER_EVENTS_CHANNELS` (comma-separated order-event channels for `/ws/orders`)
- `BINANCE_API_KEY` / `BINANCE_API_SECRET` (signed Binance REST)
- `BINANCE_ORDER_TEST_PATH` (defaults to `/api/v3/order/test`; use `/fapi/v1/order/test` for Futures API)
- `ALPACA_API_KEY` / `ALPACA_API_SECRET` / `ALPACA_TRADING_BASE_URL`
- `STRATEGY_BASE_URL` (optional strategy upstream probe for gateway `/api/v1/external/status`)
- `TRADING_POLICY_ENFORCED` (server-side risk gate)
- `BINANCE_ALLOWED_SYMBOLS` / `ALPACA_ALLOWED_SYMBOLS`
- `MAX_BINANCE_ORDER_QTY` / `MAX_BINANCE_ORDER_NOTIONAL_USD`
- `MAX_ALPACA_ORDER_QTY` / `MAX_ALPACA_LIMIT_NOTIONAL_USD`

Gateway external trading endpoints:

- `POST /api/v1/binance/order/test` (signed test endpoint, does not place real order)
- `GET /api/v1/alpaca/account`
- `POST /api/v1/alpaca/orders`

Signal persistence path:

- Ingest (Gateway/Manual) -> Strategy -> Firestore + Supabase `strategy_signals`
- Matching execution relay (Strategy) -> Redis `trade.executions.<account_id>` -> Gateway `/ws/orders`

Matching service runtime capabilities:

- Price-time priority matching core
- Order lifecycle tracking (`NEW/PARTIALLY_FILLED/FILLED/CANCELED/REJECTED`)
- Execution journal with per-account query helpers
- gRPC `OrderService` implementation (submit/cancel/get/stream) when built with gRPC deps
- gRPC health/stats endpoints for service observability (`Health`, `GetServiceStats`)
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

- Python tests (strategy)
- Rust `cargo check` (gateway)
- C++ build and tests (matching)
- Frontend unit tests + Playwright e2e + build + Lighthouse assertions
- Optional Buf checks (when `buf` is available in runner)

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
