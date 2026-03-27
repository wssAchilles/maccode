#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${1:-$(gcloud config get-value project 2>/dev/null || true)}"
REGION="${2:-asia-east2}"
SERVICE_NAME="${SERVICE_NAME:-cerberus-matching}"
SOURCE_DIR="${SOURCE_DIR:-$(cd "$(dirname "$0")/../services/matching-cpp" && pwd)}"

if [[ -z "${PROJECT_ID}" ]]; then
  echo "PROJECT_ID is required (arg1 or active gcloud project)." >&2
  exit 1
fi

MATCHING_GRPC_MAX_POLLERS="${MATCHING_GRPC_MAX_POLLERS:-8}"
MATCHING_GRPC_MIN_POLLERS="${MATCHING_GRPC_MIN_POLLERS:-4}"
MATCHING_GRPC_NUM_CQS="${MATCHING_GRPC_NUM_CQS:-4}"
MATCHING_EXECUTION_STREAM_LIMIT="${MATCHING_EXECUTION_STREAM_LIMIT:-500}"
MATCHING_SUBMIT_LATENCY_WINDOW_SIZE="${MATCHING_SUBMIT_LATENCY_WINDOW_SIZE:-1024}"
MATCHING_MAX_INFLIGHT_REQUESTS="${MATCHING_MAX_INFLIGHT_REQUESTS:-512}"
MATCHING_INFLIGHT_ACQUIRE_TIMEOUT_MS="${MATCHING_INFLIGHT_ACQUIRE_TIMEOUT_MS:-25}"
MATCHING_BACKPRESSURE_RETRY_SLEEP_MS="${MATCHING_BACKPRESSURE_RETRY_SLEEP_MS:-1}"

create_temp_env_file() {
  local prefix="$1"
  local base
  base="$(mktemp "${TMPDIR:-/tmp}/${prefix}.XXXXXX")"
  mv "${base}" "${base}.yaml"
  printf '%s.yaml\n' "${base}"
}

env_file="$(create_temp_env_file cerberus-matching-env)"
cat >"${env_file}" <<YAML
MATCHING_GRPC_MAX_POLLERS: "${MATCHING_GRPC_MAX_POLLERS}"
MATCHING_GRPC_MIN_POLLERS: "${MATCHING_GRPC_MIN_POLLERS}"
MATCHING_GRPC_NUM_CQS: "${MATCHING_GRPC_NUM_CQS}"
MATCHING_EXECUTION_STREAM_LIMIT: "${MATCHING_EXECUTION_STREAM_LIMIT}"
MATCHING_SUBMIT_LATENCY_WINDOW_SIZE: "${MATCHING_SUBMIT_LATENCY_WINDOW_SIZE}"
MATCHING_MAX_INFLIGHT_REQUESTS: "${MATCHING_MAX_INFLIGHT_REQUESTS}"
MATCHING_INFLIGHT_ACQUIRE_TIMEOUT_MS: "${MATCHING_INFLIGHT_ACQUIRE_TIMEOUT_MS}"
MATCHING_BACKPRESSURE_RETRY_SLEEP_MS: "${MATCHING_BACKPRESSURE_RETRY_SLEEP_MS}"
YAML

echo "deploying ${SERVICE_NAME} from source: ${SOURCE_DIR}"
gcloud run deploy "${SERVICE_NAME}" \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --platform=managed \
  --allow-unauthenticated \
  --use-http2 \
  --source="${SOURCE_DIR}" \
  --env-vars-file="${env_file}"

rm -f "${env_file}"
echo "deploy completed: ${SERVICE_NAME} (${PROJECT_ID}/${REGION})"
