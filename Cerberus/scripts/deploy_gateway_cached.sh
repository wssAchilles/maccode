#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/deploy_common.sh"
trap cleanup_registered_files EXIT

PROJECT_ID="${1:-$(gcloud config get-value project 2>/dev/null || true)}"
REGION="${2:-asia-east2}"
SERVICE_NAME="${SERVICE_NAME:-cerberus-gateway}"
SOURCE_DIR="${SOURCE_DIR:-$(cd "${SCRIPT_DIR}/../services/gateway-rs" && pwd)}"

if [[ -z "${PROJECT_ID}" ]]; then
  echo "PROJECT_ID is required (arg1 or active gcloud project)." >&2
  exit 1
fi

require_command gcloud

if [[ ! -d "${SOURCE_DIR}" ]]; then
  echo "SOURCE_DIR does not exist: ${SOURCE_DIR}" >&2
  exit 1
fi

validate_gateway_policy() {
  local deploy_env
  deploy_env="$(echo "${APP_ENV}" | tr '[:upper:]' '[:lower:]')"
  if [[ "${deploy_env}" == "production" ]]; then
    if [[ "${JWT_AUTH_REQUIRE_IN_PRODUCTION}" != "true" ]]; then
      echo "JWT_AUTH_REQUIRE_IN_PRODUCTION must be true when APP_ENV=production" >&2
      exit 1
    fi
    if [[ "${CORS_ALLOW_ORIGINS}" == "*" ]]; then
      echo "CORS_ALLOW_ORIGINS cannot be '*' when APP_ENV=production" >&2
      exit 1
    fi
  fi
}

REPOSITORY="${AR_REPOSITORY:-cerberus}"
IMAGE_NAME="${IMAGE_NAME:-gateway-rs}"
IMAGE_TAG="${IMAGE_TAG:-$(date +%Y%m%d-%H%M%S)}"
IMAGE_URI="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${IMAGE_NAME}:${IMAGE_TAG}"
IMAGE_LATEST="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${IMAGE_NAME}:latest"

REDIS_ORDERBOOK_CHANNEL="${REDIS_ORDERBOOK_CHANNEL:-md.orderbook.BTCUSDT}"
REDIS_ORDERBOOK_CHANNEL_PREFIX="${REDIS_ORDERBOOK_CHANNEL_PREFIX:-md.orderbook}"
REDIS_TICK_CHANNEL_PREFIX="${REDIS_TICK_CHANNEL_PREFIX:-md.ticks}"
REDIS_ORDER_EVENTS_CHANNELS="${REDIS_ORDER_EVENTS_CHANNELS:-strategy.signals.default,trade.executions.default}"
MARKET_SYMBOLS="${MARKET_SYMBOLS:-BTCUSDT,ETHUSDT}"
BINANCE_API_BASE="${BINANCE_API_BASE:-https://demo-fapi.binance.com}"
BINANCE_ORDER_TEST_PATH="${BINANCE_ORDER_TEST_PATH:-/fapi/v1/order/test}"
MARKET_WS_URL="${MARKET_WS_URL:-wss://fstream.binance.com/stream?streams=btcusdt@bookTicker/ethusdt@bookTicker}"
KLINE_API_URL="${KLINE_API_URL:-https://demo-fapi.binance.com/fapi/v1/klines}"
ALPACA_TRADING_BASE_URL="${ALPACA_TRADING_BASE_URL:-https://paper-api.alpaca.markets/v2}"
STRATEGY_BASE_URL="${STRATEGY_BASE_URL:-}"
CORS_ALLOW_ORIGINS="${CORS_ALLOW_ORIGINS:-*}"
APP_ENV="${APP_ENV:-development}"
FIREBASE_AUTH_REQUIRED="${FIREBASE_AUTH_REQUIRED:-true}"
FIREBASE_PROJECT_ID="${FIREBASE_PROJECT_ID:-${PROJECT_ID}}"
JWT_AUTH_ENABLED="${JWT_AUTH_ENABLED:-false}"
JWT_AUTH_REQUIRE_IN_PRODUCTION="${JWT_AUTH_REQUIRE_IN_PRODUCTION:-true}"
JWT_ISSUER="${JWT_ISSUER:-}"
JWT_AUDIENCE="${JWT_AUDIENCE:-}"
TRADING_POLICY_ENFORCED="${TRADING_POLICY_ENFORCED:-true}"
BINANCE_ALLOWED_SYMBOLS="${BINANCE_ALLOWED_SYMBOLS:-BTCUSDT,ETHUSDT}"
ALPACA_ALLOWED_SYMBOLS="${ALPACA_ALLOWED_SYMBOLS:-AAPL,TSLA,NVDA}"
MAX_BINANCE_ORDER_QTY="${MAX_BINANCE_ORDER_QTY:-0.05}"
MAX_BINANCE_ORDER_NOTIONAL_USD="${MAX_BINANCE_ORDER_NOTIONAL_USD:-5000}"
MAX_ALPACA_ORDER_QTY="${MAX_ALPACA_ORDER_QTY:-100}"
MAX_ALPACA_LIMIT_NOTIONAL_USD="${MAX_ALPACA_LIMIT_NOTIONAL_USD:-20000}"

REDIS_URL_SECRET="${REDIS_URL_SECRET:-cerberus-upstash-redis-url}"
FIREBASE_WEB_API_KEY_SECRET="${FIREBASE_WEB_API_KEY_SECRET:-cerberus-firebase-web-api-key}"
BINANCE_API_KEY_SECRET="${BINANCE_API_KEY_SECRET:-cerberus-binance-api-key}"
BINANCE_API_SECRET_SECRET="${BINANCE_API_SECRET_SECRET:-cerberus-binance-api-secret}"
ALPACA_API_KEY_SECRET="${ALPACA_API_KEY_SECRET:-cerberus-alpaca-api-key}"
ALPACA_API_SECRET_SECRET="${ALPACA_API_SECRET_SECRET:-cerberus-alpaca-api-secret}"
JWT_HS256_SECRET_SECRET="${JWT_HS256_SECRET_SECRET:-cerberus-jwt-hs256-secret}"

validate_gateway_policy
ensure_artifact_registry_repo "${PROJECT_ID}" "${REGION}" "${REPOSITORY}"

cloudbuild_file="$(create_temp_yaml cerberus-gateway-cloudbuild)"
register_cleanup_file "${cloudbuild_file}"
cat >"${cloudbuild_file}" <<YAML
steps:
  - name: gcr.io/cloud-builders/docker
    entrypoint: bash
    args:
      - -lc
      - docker pull ${IMAGE_LATEST} || true
  - name: gcr.io/cloud-builders/docker
    args:
      - build
      - --cache-from
      - ${IMAGE_LATEST}
      - -t
      - ${IMAGE_URI}
      - -t
      - ${IMAGE_LATEST}
      - .
images:
  - ${IMAGE_URI}
  - ${IMAGE_LATEST}
YAML

echo "building cached image: ${IMAGE_URI}"
run_cmd gcloud builds submit "${SOURCE_DIR}" \
  --project="${PROJECT_ID}" \
  --config="${cloudbuild_file}" \
  --ignore-file="${SOURCE_DIR}/.gcloudignore" \
  $(gcloud_quiet_args)

env_file="$(create_temp_yaml cerberus-gateway-env)"
register_cleanup_file "${env_file}"
cat >"${env_file}" <<YAML
REDIS_ORDERBOOK_CHANNEL: ${REDIS_ORDERBOOK_CHANNEL}
REDIS_ORDERBOOK_CHANNEL_PREFIX: ${REDIS_ORDERBOOK_CHANNEL_PREFIX}
REDIS_TICK_CHANNEL_PREFIX: ${REDIS_TICK_CHANNEL_PREFIX}
REDIS_ORDER_EVENTS_CHANNELS: "${REDIS_ORDER_EVENTS_CHANNELS}"
MARKET_SYMBOLS: "${MARKET_SYMBOLS}"
BINANCE_API_BASE: ${BINANCE_API_BASE}
BINANCE_ORDER_TEST_PATH: ${BINANCE_ORDER_TEST_PATH}
MARKET_WS_URL: ${MARKET_WS_URL}
KLINE_API_URL: ${KLINE_API_URL}
ALPACA_TRADING_BASE_URL: ${ALPACA_TRADING_BASE_URL}
STRATEGY_BASE_URL: "${STRATEGY_BASE_URL}"
CORS_ALLOW_ORIGINS: "${CORS_ALLOW_ORIGINS}"
APP_ENV: "${APP_ENV}"
FIREBASE_AUTH_REQUIRED: "${FIREBASE_AUTH_REQUIRED}"
FIREBASE_PROJECT_ID: "${FIREBASE_PROJECT_ID}"
JWT_AUTH_ENABLED: "${JWT_AUTH_ENABLED}"
JWT_AUTH_REQUIRE_IN_PRODUCTION: "${JWT_AUTH_REQUIRE_IN_PRODUCTION}"
JWT_ISSUER: "${JWT_ISSUER}"
JWT_AUDIENCE: "${JWT_AUDIENCE}"
TRADING_POLICY_ENFORCED: "${TRADING_POLICY_ENFORCED}"
BINANCE_ALLOWED_SYMBOLS: "${BINANCE_ALLOWED_SYMBOLS}"
ALPACA_ALLOWED_SYMBOLS: "${ALPACA_ALLOWED_SYMBOLS}"
MAX_BINANCE_ORDER_QTY: "${MAX_BINANCE_ORDER_QTY}"
MAX_BINANCE_ORDER_NOTIONAL_USD: "${MAX_BINANCE_ORDER_NOTIONAL_USD}"
MAX_ALPACA_ORDER_QTY: "${MAX_ALPACA_ORDER_QTY}"
MAX_ALPACA_LIMIT_NOTIONAL_USD: "${MAX_ALPACA_LIMIT_NOTIONAL_USD}"
YAML

echo "deploying image to Cloud Run service: ${SERVICE_NAME}"
run_cmd gcloud run deploy "${SERVICE_NAME}" \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --platform=managed \
  --allow-unauthenticated \
  --image="${IMAGE_URI}" \
  --env-vars-file="${env_file}" \
  --set-secrets="REDIS_URL=${REDIS_URL_SECRET}:latest,FIREBASE_WEB_API_KEY=${FIREBASE_WEB_API_KEY_SECRET}:latest,JWT_HS256_SECRET=${JWT_HS256_SECRET_SECRET}:latest,BINANCE_API_KEY=${BINANCE_API_KEY_SECRET}:latest,BINANCE_API_SECRET=${BINANCE_API_SECRET_SECRET}:latest,ALPACA_API_KEY=${ALPACA_API_KEY_SECRET}:latest,ALPACA_API_SECRET=${ALPACA_API_SECRET_SECRET}:latest" \
  $(gcloud_quiet_args)

echo "cached deploy completed: ${SERVICE_NAME} (${PROJECT_ID}/${REGION})"
echo "image: ${IMAGE_URI}"
