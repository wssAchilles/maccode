# Secrets and Firebase Integration

## Gurobi WLS

Runtime variables expected by strategy service:

- `GRB_LICENSEID`
- `GRB_WLSACCESSID`
- `GRB_WLSSECRET`

Local development:

- Copy `deploy/compose/.env.example` to `.env` and set values.

Cloud deployment:

- Store values in GCP Secret Manager.
- Terraform maps secrets to Cloud Run env vars.

## Exchange Secrets (Binance + Alpaca)

Gateway runtime variables:

- `BINANCE_API_BASE` (for futures test key use `https://demo-fapi.binance.com`)
- `BINANCE_ORDER_TEST_PATH` (spot `/api/v3/order/test`, futures `/fapi/v1/order/test`)
- `MARKET_WS_URL` (optional explicit stream endpoint)
- `KLINE_API_URL` (optional explicit kline endpoint)
- `MARKET_SYMBOLS` (e.g. `BTCUSDT,ETHUSDT`)
- `REDIS_ORDERBOOK_CHANNEL_PREFIX` (default `md.orderbook`)
- `REDIS_TICK_CHANNEL_PREFIX` (default `md.ticks`)
- `BINANCE_API_KEY` (Secret Manager)
- `BINANCE_API_SECRET` (Secret Manager)
- `ALPACA_TRADING_BASE_URL` (default `https://paper-api.alpaca.markets/v2`)
- `ALPACA_API_KEY` (Secret Manager)
- `ALPACA_API_SECRET` (Secret Manager)

Recommended secret names:

- `cerberus-binance-api-key`
- `cerberus-binance-api-secret`
- `cerberus-alpaca-api-key`
- `cerberus-alpaca-api-secret`

Automated sync + deploy:

```bash
export BINANCE_API_KEY=...
export BINANCE_API_SECRET=...
export ALPACA_API_KEY=...
export ALPACA_API_SECRET=...
./scripts/sync_gcp_exchange_secrets.sh cerberus-9d94f asia-east2
./scripts/deploy_gateway_source.sh cerberus-9d94f asia-east2
./scripts/deploy_strategy_source.sh cerberus-9d94f asia-east2
```

## Supabase

Runtime variables expected by strategy service:

- `SUPABASE_ENABLED=true`
- `SUPABASE_PROJECT_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_SIGNAL_TABLE=strategy_signals`
- `SUPABASE_DB_URL` (for bootstrap/migrations scripts)

## Firebase

Frontend reads Firebase config from Vite env vars:

- `VITE_FIREBASE_API_KEY`
- `VITE_FIREBASE_AUTH_DOMAIN`
- `VITE_FIREBASE_PROJECT_ID`
- `VITE_FIREBASE_STORAGE_BUCKET`
- `VITE_FIREBASE_MESSAGING_SENDER_ID`
- `VITE_FIREBASE_APP_ID`

The app initializes Firebase only when required fields are present.

Strategy service optional Firestore persistence:

- `FIREBASE_ENABLED=true`
- `FIREBASE_PROJECT_ID=cerberus-9d94f`
- `FIREBASE_SIGNAL_COLLECTION=strategy_signals`

Strategy CORS:

- `CORS_ALLOW_ORIGINS=*` (or comma-separated allowlist for production)
