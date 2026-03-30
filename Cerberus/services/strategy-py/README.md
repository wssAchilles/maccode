# cerberus-strategy

Quant strategy service.

Startup policy:

- Runtime validates critical settings at startup and fails fast on invalid combinations.
- Set `APP_ENV=production` to enable stricter production policy checks (for example, wildcard CORS rejection).
- In production, `MARKET_STREAM_LEGACY_PUBSUB_FALLBACK` and `EVENT_STREAM_PUBLISH_LEGACY_PUBSUB` must be `false` (startup hard-fail on violation).

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
- `EVENT_SCHEMA_VERSION=v1`
- `EVENT_STREAM_MAXLEN=10000`
- `EVENT_STREAM_PUBLISH_LEGACY_PUBSUB=true` (set `false` for strict stream-only publish)
- `IDEMPOTENCY_STORE_REDIS_ENABLED=true`
- `IDEMPOTENCY_REDIS_KEY_PREFIX=cerberus:idempotency`
- `SIGNAL_IDEMPOTENCY_TTL_SECONDS=900`

Optional research / inference baseline:

- `INFERENCE_ENABLED=false`
- `INFERENCE_MODE=disabled` (`observe` and `primary` are also supported)
- `INFERENCE_ENGINE_NAME=moving_average_baseline`
- `INFERENCE_MODEL_ID=moving-average-baseline`
- `INFERENCE_MODEL_VERSION=v1`
- `INFERENCE_MODEL_SOURCE=runtime`
- `INFERENCE_MODEL_SYMBOLS=BTCUSDT,ETHUSDT`
- `INFERENCE_ARTIFACT_FOLDER_URL=` (required when `INFERENCE_MODEL_SOURCE=google_drive`)
- `INFERENCE_ARTIFACT_GCS_URI=` (required when `INFERENCE_MODEL_SOURCE=gcs`)
- `INFERENCE_ARTIFACT_CACHE_DIR=/tmp/cerberus-inference`
- `INFERENCE_PRIMARY_MIN_MACRO_F1=0.58`
- `INFERENCE_PRIMARY_MIN_OBSERVE_TICKS=500`
- `INFERENCE_PRIMARY_MIN_AGREEMENT_RATIO=0.55`
- `INFERENCE_ROLLOUT_FORCE_PRIMARY=false`
- `INFERENCE_AUDIT_MAX_EVENTS=50`

Google Drive artifact-backed inference:

- Set `INFERENCE_MODEL_SOURCE=google_drive`
- Point `INFERENCE_ARTIFACT_FOLDER_URL` at a shared `best_model` folder
- Required files in the folder:
  - `artifact_manifest.json`
  - `training_metrics.json`
  - `cerberus_signal_model.onnx`
  - `preprocessing.json` (preferred)
  - `cerberus_signal_model.pt` (fallback for legacy bundles)
- Runtime will:
  - resolve file IDs from the shared folder page
  - download and cache artifacts under `INFERENCE_ARTIFACT_CACHE_DIR`
  - load preprocessing metadata from `preprocessing.json` when present
  - otherwise extract preprocessing metadata from `cerberus_signal_model.pt`
  - run online ONNX inference over the live tick stream

GCS artifact-backed inference:

- Set `INFERENCE_MODEL_SOURCE=gcs`
- Point `INFERENCE_ARTIFACT_GCS_URI` at the `best_model` prefix, for example:
  - `gs://cerberus-9d94f-models-20260330-ae2/models/cerberus-transformer-lstm/v1/best_model`
- Required objects under that prefix:
  - `artifact_manifest.json`
  - `training_metrics.json`
  - `cerberus_signal_model.onnx`
  - `preprocessing.json` (preferred)
  - `cerberus_signal_model.pt` (fallback for legacy bundles)
- Runtime will:
  - download and cache artifacts under `INFERENCE_ARTIFACT_CACHE_DIR`
  - load preprocessing metadata from `preprocessing.json` when present
  - otherwise extract preprocessing metadata from `cerberus_signal_model.pt`
  - run online ONNX inference over the live tick stream

Market subscriptions:

- `MARKET_CHANNEL=md.orderbook.BTCUSDT` (single channel fallback)
- `MARKET_CHANNELS=md.orderbook.BTCUSDT,md.orderbook.ETHUSDT` (preferred multi-channel mode)
- `MARKET_STREAM_ENABLED=true` (primary market ingest mode)
- `MARKET_STREAM_KEY=cerberus.market.events`
- `MARKET_STREAM_CONSUMER_GROUP=strategy-market`
- `MARKET_STREAM_CONSUMER_NAME=` (optional override; auto-generated when empty)
- `MARKET_STREAM_LEGACY_PUBSUB_FALLBACK=true`

Runtime module skeleton:

- `app/market_ingest_runtime/loop.py`: market ingest mode orchestrator
- `app/market_ingest_runtime/pubsub_runtime.py`: legacy pub/sub ingest loop
- `app/market_ingest_runtime/stream_runtime.py`: stream consumer-group main loop + maintenance
- `app/market_ingest_runtime/stream_io.py`: stream read/ack/backlog parsing helpers
- `app/market_ingest_runtime/stream_processing.py`: entry decode + batch processing
- `app/market_ingest_runtime/stream_reclaim.py`: reclaim + poison routing
- `app/event_runtime/publish.py`: generic publish path + signal event encode
- `app/event_runtime/matching_submission.py`: matching submit event orchestration
- `app/event_runtime/relay.py`: execution relay loop + batch builders
- `app/event_runtime/envelope.py`: canonical event envelope builder
- `app/matching_service/service.py`: matching API orchestration service
- `app/matching_service/{mapping,filters,fallbacks}.py`: response mapping/filtering/degraded fallback helpers

Signal smoke endpoint (works without Redis):

- `POST /api/v1/signal/ingest`

Runtime introspection endpoints:

- `GET /ready`
- `GET /metrics` (Prometheus)
- `GET /api/v1/signals/recent?limit=20&source=auto`
- `GET /api/v1/status/persistence`
- `GET /api/v1/inference/status`
- `GET /api/v1/inference/models`
- `GET /api/v1/inference/audit`

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
- Strategy order submit forwards `idempotency_key` (HTTP `idempotency-key` or signal-derived key).
- Redis signal path batches `strategy.signal.generated` and optional `matching.order.submitted` into one pipeline write.
- Strategy HTTP middleware preserves incoming `x-request-id` (or generates one) and echoes it in response headers.
- HTTP errors are wrapped as `{ "error": { "code", "message", "request_id" } }`.
- `/api/v1/status/persistence` now includes `matching.health` and `matching.stats`.
- `/metrics` exposes Prometheus counters/gauges for worker loops, signal throughput, storage toggles, matching reachability, and matching degraded state.
- `/metrics` includes stream-mode policy gauges (`market_stream_legacy_pubsub_fallback_enabled`, `event_stream_legacy_pubsub_publish_enabled`) for drift detection.
- `/metrics` also exposes market stream consumer-group health (`market_stream_events`, ack/read failures, retry/fallback counters, ingest mode).
- `matching.stats` includes matching capacity baselines from gRPC:
  - submit request/error/rejection counters
  - `submit_order_latency_p95_ms`
  - `submit_order_throughput_rps` and `trade_throughput_rps`
