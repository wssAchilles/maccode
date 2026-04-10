#!/bin/bash

# ===================================
# Cloud Run Backend Deployment Script
# Optimized for "Dual-Core" Architecture (On-Demand High Performance)
# Cost Strategy: Min Instances = 0 (Pay only when used)
# ===================================

set -e  # Exit immediately if a command exits with a non-zero status.

GCLOUD_BIN="${GCLOUD_BIN:-}"
CLOUDSDK_PYTHON_BIN="${CLOUDSDK_PYTHON:-}"
if [ -z "$CLOUDSDK_PYTHON_BIN" ] && [ -x "/Users/achilles/Documents/code/data science/venv/bin/python" ]; then
    CLOUDSDK_PYTHON_BIN="/Users/achilles/Documents/code/data science/venv/bin/python"
fi
if [ -z "$GCLOUD_BIN" ]; then
    if command -v gcloud >/dev/null 2>&1; then
        GCLOUD_BIN="$(command -v gcloud)"
    elif [ -x "/Users/achilles/development/google-cloud-sdk/bin/gcloud" ]; then
        GCLOUD_BIN="/Users/achilles/development/google-cloud-sdk/bin/gcloud"
    else
        echo "❌ Error: gcloud is required to deploy Cloud Run."
        exit 1
    fi
fi

if [ -n "$CLOUDSDK_PYTHON_BIN" ]; then
    export CLOUDSDK_PYTHON="$CLOUDSDK_PYTHON_BIN"
fi

echo "🚀 Starting Cloud Run Deployment Sequence..."

# 1. Project Setup
PROJECT_ID=$("$GCLOUD_BIN" config get-value project)
echo "✅ Project ID: $PROJECT_ID"

if [ -z "$PROJECT_ID" ]; then
    echo "❌ Error: Could not determine Google Cloud Project ID."
    echo "Please run 'gcloud config set project <YOUR_PROJECT_ID>' first."
    exit 1
fi

SERVICE_NAME="sentinel-backend-cloudrun"
REGION="us-central1" # Or allow user to override
INTERNAL_JOB_TOKEN="${INTERNAL_JOB_TOKEN:-dev-internal-job-token}"
GCP_PROJECT_ID="${GCP_PROJECT_ID:-$PROJECT_ID}"
FIRESTORE_DATABASE="${FIRESTORE_DATABASE:-my-datasci-project-bucket}"
STORAGE_BUCKET_NAME="${STORAGE_BUCKET_NAME:-data-science-44398.firebasestorage.app}"
CLOUD_RUN_SERVICE_ACCOUNT="${CLOUD_RUN_SERVICE_ACCOUNT:-${PROJECT_ID}@appspot.gserviceaccount.com}"
FLASK_ENV="${FLASK_ENV:-production}"
INTERNAL_BASE_URL="${INTERNAL_BASE_URL:-https://${PROJECT_ID}.an.r.appspot.com}"
TASKS_EXECUTION_MODE="${TASKS_EXECUTION_MODE:-cloud_tasks}"
TASKS_LOCATION="${TASKS_LOCATION:-asia-northeast1}"
TASKS_QUEUE_NAME="${TASKS_QUEUE_NAME:-industrial-jobs}"
ML_TRAIN_BACKEND_DEFAULT="${ML_TRAIN_BACKEND_DEFAULT:-vertex_custom_training}"
ML_TRAIN_VERTEX_ENABLED="${ML_TRAIN_VERTEX_ENABLED:-true}"
ML_TRAIN_VERTEX_ROLLOUT_MODE="${ML_TRAIN_VERTEX_ROLLOUT_MODE:-manual_all}"
ML_TRAIN_VERTEX_MIN_FILE_SIZE_BYTES="${ML_TRAIN_VERTEX_MIN_FILE_SIZE_BYTES:-0}"
ML_TRAIN_VERTEX_MAX_PARALLEL_JOBS="${ML_TRAIN_VERTEX_MAX_PARALLEL_JOBS:-2}"
ML_TRAIN_VERTEX_MAX_RUNTIME_S="${ML_TRAIN_VERTEX_MAX_RUNTIME_S:-7200}"
ML_TRAIN_VERTEX_CPU_ONLY="${ML_TRAIN_VERTEX_CPU_ONLY:-true}"
ML_TRAIN_VERTEX_RECONCILE_DELAY_S="${ML_TRAIN_VERTEX_RECONCILE_DELAY_S:-30}"
VERTEX_REGION="${VERTEX_REGION:-us-central1}"
VERTEX_TRAINING_IMAGE_URI="${VERTEX_TRAINING_IMAGE_URI:-us-central1-docker.pkg.dev/${PROJECT_ID}/sentinel-jobs/vertex-trainer:latest}"
VERTEX_TRAINING_STAGING_BUCKET="${VERTEX_TRAINING_STAGING_BUCKET:-${PROJECT_ID}-vertex-training-us-central1}"
VERTEX_TRAINING_SERVICE_ACCOUNT="${VERTEX_TRAINING_SERVICE_ACCOUNT:-vertex-trainer-sa@${PROJECT_ID}.iam.gserviceaccount.com}"
VERTEX_TRAINING_MACHINE_TYPE="${VERTEX_TRAINING_MACHINE_TYPE:-n1-standard-4}"
VERTEX_TRAINING_ACCELERATOR_TYPE="${VERTEX_TRAINING_ACCELERATOR_TYPE:-}"
VERTEX_TRAINING_ACCELERATOR_COUNT="${VERTEX_TRAINING_ACCELERATOR_COUNT:-0}"
TRAINING_CALLBACK_BASE_URL="${TRAINING_CALLBACK_BASE_URL:-$INTERNAL_BASE_URL}"
COMPUTE_NATIVE_ENABLED="${COMPUTE_NATIVE_ENABLED:-true}"
COMPUTE_NATIVE_MODULE="${COMPUTE_NATIVE_MODULE:-rolling_features_native}"
COMPUTE_PROFILE_ENABLED="${COMPUTE_PROFILE_ENABLED:-true}"
COMPUTE_NATIVE_GUARD_ENABLED="${COMPUTE_NATIVE_GUARD_ENABLED:-true}"
COMPUTE_NATIVE_GUARD_FAILURE_THRESHOLD="${COMPUTE_NATIVE_GUARD_FAILURE_THRESHOLD:-3}"
COMPUTE_NATIVE_GUARD_WINDOW_MINUTES="${COMPUTE_NATIVE_GUARD_WINDOW_MINUTES:-30}"
COMPUTE_FEATURE_NATIVE_MIN_SPEEDUP="${COMPUTE_FEATURE_NATIVE_MIN_SPEEDUP:-1.15}"
COMPUTE_SCENARIO_VECTOR_MIN_SPEEDUP="${COMPUTE_SCENARIO_VECTOR_MIN_SPEEDUP:-1.05}"
COMPUTE_BENCHMARK_STALE_HOURS="${COMPUTE_BENCHMARK_STALE_HOURS:-168}"
RAG_BACKEND_MODE="${RAG_BACKEND_MODE:-storage_fallback}"

# 2. Build Container Image
# We use Cloud Build to build the image remotely.
# This avoids local Docker dependency issues and uses the cloud's bandwidth.
echo "🏗️  Building Container Image (this may take a few minutes)..."
echo "   Target: gcr.io/$PROJECT_ID/$SERVICE_NAME"

# Ensure we are in the root directory (where scripts/ is) or correct relative path
# The script is likely run from root, so back/ is the context.
if [ -d "back" ]; then
    BUILD_CONTEXT="back"
else
    echo "❌ Error: Could not find 'back' directory. Please run this script from the project root."
    exit 1
fi

"$GCLOUD_BIN" builds submit "$BUILD_CONTEXT" \
    --tag "gcr.io/$PROJECT_ID/$SERVICE_NAME" \
    --quiet

echo "✅ Build Successful."

# 3. Deploy to Cloud Run
echo "📦 Deploying to Cloud Run..."
echo "   Configuration: 4Gi Memory, 2 vCPU, 1800s Timeout, Min Instances 0 (Cost Saving)"

"$GCLOUD_BIN" run deploy "$SERVICE_NAME" \
    --image "gcr.io/$PROJECT_ID/$SERVICE_NAME" \
    --platform managed \
    --region "$REGION" \
    --allow-unauthenticated \
    --service-account "$CLOUD_RUN_SERVICE_ACCOUNT" \
    --memory 4Gi \
    --cpu 2 \
    --timeout 1800 \
    --concurrency 8 \
    --min-instances 0 \
    --max-instances 3 \
    --set-env-vars "FLASK_ENV=${FLASK_ENV},GCP_PROJECT_ID=${GCP_PROJECT_ID},FIRESTORE_DATABASE=${FIRESTORE_DATABASE},STORAGE_BUCKET_NAME=${STORAGE_BUCKET_NAME},INTERNAL_JOB_TOKEN=${INTERNAL_JOB_TOKEN},INTERNAL_BASE_URL=${INTERNAL_BASE_URL},TASKS_EXECUTION_MODE=${TASKS_EXECUTION_MODE},TASKS_LOCATION=${TASKS_LOCATION},TASKS_QUEUE_NAME=${TASKS_QUEUE_NAME},ML_TRAIN_BACKEND_DEFAULT=${ML_TRAIN_BACKEND_DEFAULT},ML_TRAIN_VERTEX_ENABLED=${ML_TRAIN_VERTEX_ENABLED},ML_TRAIN_VERTEX_ROLLOUT_MODE=${ML_TRAIN_VERTEX_ROLLOUT_MODE},ML_TRAIN_VERTEX_MIN_FILE_SIZE_BYTES=${ML_TRAIN_VERTEX_MIN_FILE_SIZE_BYTES},ML_TRAIN_VERTEX_MAX_PARALLEL_JOBS=${ML_TRAIN_VERTEX_MAX_PARALLEL_JOBS},ML_TRAIN_VERTEX_MAX_RUNTIME_S=${ML_TRAIN_VERTEX_MAX_RUNTIME_S},ML_TRAIN_VERTEX_CPU_ONLY=${ML_TRAIN_VERTEX_CPU_ONLY},ML_TRAIN_VERTEX_RECONCILE_DELAY_S=${ML_TRAIN_VERTEX_RECONCILE_DELAY_S},VERTEX_REGION=${VERTEX_REGION},VERTEX_TRAINING_IMAGE_URI=${VERTEX_TRAINING_IMAGE_URI},VERTEX_TRAINING_STAGING_BUCKET=${VERTEX_TRAINING_STAGING_BUCKET},VERTEX_TRAINING_SERVICE_ACCOUNT=${VERTEX_TRAINING_SERVICE_ACCOUNT},VERTEX_TRAINING_MACHINE_TYPE=${VERTEX_TRAINING_MACHINE_TYPE},VERTEX_TRAINING_ACCELERATOR_TYPE=${VERTEX_TRAINING_ACCELERATOR_TYPE},VERTEX_TRAINING_ACCELERATOR_COUNT=${VERTEX_TRAINING_ACCELERATOR_COUNT},TRAINING_CALLBACK_BASE_URL=${TRAINING_CALLBACK_BASE_URL},COMPUTE_NATIVE_ENABLED=${COMPUTE_NATIVE_ENABLED},COMPUTE_NATIVE_MODULE=${COMPUTE_NATIVE_MODULE},COMPUTE_PROFILE_ENABLED=${COMPUTE_PROFILE_ENABLED},COMPUTE_NATIVE_GUARD_ENABLED=${COMPUTE_NATIVE_GUARD_ENABLED},COMPUTE_NATIVE_GUARD_FAILURE_THRESHOLD=${COMPUTE_NATIVE_GUARD_FAILURE_THRESHOLD},COMPUTE_NATIVE_GUARD_WINDOW_MINUTES=${COMPUTE_NATIVE_GUARD_WINDOW_MINUTES},COMPUTE_FEATURE_NATIVE_MIN_SPEEDUP=${COMPUTE_FEATURE_NATIVE_MIN_SPEEDUP},COMPUTE_SCENARIO_VECTOR_MIN_SPEEDUP=${COMPUTE_SCENARIO_VECTOR_MIN_SPEEDUP},COMPUTE_BENCHMARK_STALE_HOURS=${COMPUTE_BENCHMARK_STALE_HOURS},RAG_BACKEND_MODE=${RAG_BACKEND_MODE}" \
    --quiet

# 4. Success Output
echo "✅ Deployment Complete!"
SERVICE_URL=$("$GCLOUD_BIN" run services describe $SERVICE_NAME --platform managed --region $REGION --format 'value(status.url)')
echo "🌐 Service URL: $SERVICE_URL"
echo ""
echo "👉 Next Step: Update your Frontend configuration with this URL."
