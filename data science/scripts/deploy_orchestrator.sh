#!/bin/bash

# ===================================
# Sentinel Orchestrator Deployment Script
# Deploys the Rust control-plane sidecar to Cloud Run.
# ===================================

set -euo pipefail

echo "🚀 Starting Sentinel Orchestrator deployment..."

PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
REGION="${REGION:-asia-northeast1}"
SERVICE_NAME="${ORCHESTRATOR_SERVICE_NAME:-sentinel-orchestrator}"
PYTHON_WORKER_BASE_URL="${PYTHON_WORKER_BASE_URL:-https://${PROJECT_ID}.an.r.appspot.com}"
INTERNAL_JOB_TOKEN="${INTERNAL_JOB_TOKEN:-dev-internal-job-token}"
MAX_LIGHT_PARALLEL="${MAX_LIGHT_PARALLEL:-4}"
MAX_HEAVY_PARALLEL="${MAX_HEAVY_PARALLEL:-2}"
DISPATCH_TIMEOUT_SECS="${DISPATCH_TIMEOUT_SECS:-1800}"

if [ -z "${PROJECT_ID}" ]; then
  echo "❌ Error: Could not determine Google Cloud Project ID."
  echo "Please run 'gcloud config set project <YOUR_PROJECT_ID>' first."
  exit 1
fi

if [ ! -d "sentinel-orchestrator" ]; then
  echo "❌ Error: Could not find 'sentinel-orchestrator' directory."
  echo "Please run this script from the project root."
  exit 1
fi

echo "✅ Project ID: ${PROJECT_ID}"
echo "✅ Region: ${REGION}"
echo "✅ Python Worker Base URL: ${PYTHON_WORKER_BASE_URL}"
echo "✅ Light Parallelism: ${MAX_LIGHT_PARALLEL}"
echo "✅ Heavy Parallelism: ${MAX_HEAVY_PARALLEL}"

echo "🏗️  Building orchestrator image..."
gcloud builds submit "sentinel-orchestrator" \
  --tag "gcr.io/${PROJECT_ID}/${SERVICE_NAME}" \
  --quiet

echo "📦 Deploying orchestrator to Cloud Run..."
gcloud run deploy "${SERVICE_NAME}" \
  --image "gcr.io/${PROJECT_ID}/${SERVICE_NAME}" \
  --platform managed \
  --region "${REGION}" \
  --allow-unauthenticated \
  --memory 512Mi \
  --cpu 1 \
  --timeout 60 \
  --concurrency 80 \
  --min-instances 0 \
  --max-instances 2 \
  --set-env-vars "PYTHON_WORKER_BASE_URL=${PYTHON_WORKER_BASE_URL},INTERNAL_JOB_TOKEN=${INTERNAL_JOB_TOKEN},MAX_LIGHT_PARALLEL=${MAX_LIGHT_PARALLEL},MAX_HEAVY_PARALLEL=${MAX_HEAVY_PARALLEL},DISPATCH_TIMEOUT_SECS=${DISPATCH_TIMEOUT_SECS}" \
  --quiet

SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" \
  --platform managed \
  --region "${REGION}" \
  --format 'value(status.url)')

echo "✅ Orchestrator deployment complete."
echo "🌐 Service URL: ${SERVICE_URL}"

echo "🩺 Verifying /readyz ..."
curl --fail --silent --show-error "${SERVICE_URL}/readyz" >/dev/null
echo "✅ Health check passed."
echo ""
echo "👉 Next step:"
echo "   Set ORCHESTRATOR_BASE_URL=${SERVICE_URL} in App Engine or Python worker env vars."
