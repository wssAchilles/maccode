#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/deploy_common.sh"
trap cleanup_registered_files EXIT

PROJECT_ID="${1:-$(gcloud config get-value project 2>/dev/null || true)}"
REGION="${2:-asia-east2}"
SERVICE_NAME="${SERVICE_NAME:-cerberus-matching}"
SOURCE_DIR="${SOURCE_DIR:-$(cd "${SCRIPT_DIR}/../services/matching-cpp" && pwd)}"
REPOSITORY="${AR_REPOSITORY:-cerberus}"
IMAGE_NAME="${IMAGE_NAME:-matching-cpp}"
IMAGE_TAG="${IMAGE_TAG:-$(date +%Y%m%d-%H%M%S)}"
IMAGE_URI="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${IMAGE_NAME}:${IMAGE_TAG}"
IMAGE_LATEST="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${IMAGE_NAME}:latest"

if [[ -z "${PROJECT_ID}" ]]; then
  echo "PROJECT_ID is required (arg1 or active gcloud project)." >&2
  exit 1
fi

require_command gcloud

if [[ ! -d "${SOURCE_DIR}" ]]; then
  echo "SOURCE_DIR does not exist: ${SOURCE_DIR}" >&2
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

ensure_artifact_registry_repo "${PROJECT_ID}" "${REGION}" "${REPOSITORY}"

cloudbuild_file="$(create_temp_yaml cerberus-matching-cloudbuild)"
register_cleanup_file "${cloudbuild_file}"
cat >"${cloudbuild_file}" <<YAML
steps:
  - name: gcr.io/cloud-builders/docker
    args:
      - build
      - -t
      - ${IMAGE_URI}
      - -t
      - ${IMAGE_LATEST}
      - .
images:
  - ${IMAGE_URI}
  - ${IMAGE_LATEST}
YAML

env_file="$(create_temp_yaml cerberus-matching-env)"
register_cleanup_file "${env_file}"
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

echo "building image from source: ${SOURCE_DIR}"
run_cmd gcloud builds submit "${SOURCE_DIR}" \
  --project="${PROJECT_ID}" \
  --config="${cloudbuild_file}" \
  --ignore-file="${SOURCE_DIR}/.gcloudignore" \
  $(gcloud_quiet_args)

echo "deploying image to Cloud Run service: ${SERVICE_NAME}"
run_cmd gcloud run deploy "${SERVICE_NAME}" \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --platform=managed \
  --allow-unauthenticated \
  --use-http2 \
  --image="${IMAGE_URI}" \
  --env-vars-file="${env_file}" \
  $(gcloud_quiet_args)

echo "source deploy completed: ${SERVICE_NAME} (${PROJECT_ID}/${REGION})"
echo "image: ${IMAGE_URI}"
