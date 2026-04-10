#!/bin/bash

set -euo pipefail

GCLOUD_BIN="${GCLOUD_BIN:-$(command -v gcloud)}"
if [ -z "$GCLOUD_BIN" ]; then
  echo "❌ Error: gcloud is required."
  exit 1
fi

PROJECT_ID="${PROJECT_ID:-$("$GCLOUD_BIN" config get-value project)}"
REGION="${VERTEX_REGION:-us-central1}"
REPOSITORY="${VERTEX_TRAINING_REPOSITORY:-sentinel-jobs}"
IMAGE_NAME="${VERTEX_TRAINING_IMAGE_NAME:-vertex-trainer}"
IMAGE_URI="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${IMAGE_NAME}:latest"
TRAINING_REQUIREMENTS_FILE="${VERTEX_TRAINING_REQUIREMENTS_FILE:-back/requirements.vertex_training.txt}"
if [ ! -f "$TRAINING_REQUIREMENTS_FILE" ]; then
  echo "❌ Error: training requirements file not found at $TRAINING_REQUIREMENTS_FILE"
  exit 1
fi

hash_file() {
  local target="$1"
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$target" | awk '{print substr($1, 1, 16)}'
  elif command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$target" | awk '{print substr($1, 1, 16)}'
  else
    python3 - <<'PY' "$target"
import hashlib
import pathlib
import sys

print(hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest()[:16])
PY
  fi
}

REQUIREMENTS_HASH="$(hash_file "$TRAINING_REQUIREMENTS_FILE")"
BASE_IMAGE_NAME="${VERTEX_TRAINING_BASE_IMAGE_NAME:-vertex-trainer-base}"
BASE_IMAGE_URI="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${BASE_IMAGE_NAME}:${REQUIREMENTS_HASH}"
STAGING_BUCKET="${VERTEX_TRAINING_STAGING_BUCKET:-${PROJECT_ID}-vertex-training-${REGION}}"
TRAINER_SA_NAME="${VERTEX_TRAINING_SERVICE_ACCOUNT_NAME:-vertex-trainer-sa}"
TRAINER_SA_EMAIL="${TRAINER_SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
APPSPOT_SA="${PROJECT_ID}@appspot.gserviceaccount.com"
PROJECT_NUMBER="$("$GCLOUD_BIN" projects describe "$PROJECT_ID" --format='value(projectNumber)')"
VERTEX_SERVICE_AGENT="service-${PROJECT_NUMBER}@gcp-sa-aiplatform.iam.gserviceaccount.com"
CLOUDBUILD_SA="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"
COMPUTE_DEFAULT_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

echo "🚀 Deploying Vertex training runtime"
echo "   Project: $PROJECT_ID"
echo "   Region:  $REGION"
echo "   Image:   $IMAGE_URI"
echo "   Base:    $BASE_IMAGE_URI"
echo "   Bucket:  gs://$STAGING_BUCKET"

"$GCLOUD_BIN" services enable \
  aiplatform.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  iamcredentials.googleapis.com \
  --project "$PROJECT_ID" \
  --quiet

"$GCLOUD_BIN" beta services identity create \
  --service=aiplatform.googleapis.com \
  --project "$PROJECT_ID" \
  --quiet >/dev/null || true

if ! "$GCLOUD_BIN" artifacts repositories describe "$REPOSITORY" --location "$REGION" --project "$PROJECT_ID" >/dev/null 2>&1; then
  "$GCLOUD_BIN" artifacts repositories create "$REPOSITORY" \
    --repository-format=docker \
    --location="$REGION" \
    --description="Sentinel Ops training images" \
    --project "$PROJECT_ID" \
    --quiet
fi

if ! "$GCLOUD_BIN" storage buckets describe "gs://${STAGING_BUCKET}" --project "$PROJECT_ID" >/dev/null 2>&1; then
  "$GCLOUD_BIN" storage buckets create "gs://${STAGING_BUCKET}" \
    --location="$REGION" \
    --project "$PROJECT_ID" \
    --uniform-bucket-level-access
fi

if ! "$GCLOUD_BIN" iam service-accounts describe "$TRAINER_SA_EMAIL" --project "$PROJECT_ID" >/dev/null 2>&1; then
  "$GCLOUD_BIN" iam service-accounts create "$TRAINER_SA_NAME" \
    --display-name="Vertex training runtime" \
    --project "$PROJECT_ID"
fi

"$GCLOUD_BIN" projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${TRAINER_SA_EMAIL}" \
  --role="roles/storage.objectAdmin" \
  --condition=None \
  --quiet >/dev/null

"$GCLOUD_BIN" projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${TRAINER_SA_EMAIL}" \
  --role="roles/logging.logWriter" \
  --condition=None \
  --quiet >/dev/null

"$GCLOUD_BIN" projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${APPSPOT_SA}" \
  --role="roles/aiplatform.user" \
  --condition=None \
  --quiet >/dev/null

"$GCLOUD_BIN" iam service-accounts add-iam-policy-binding "$TRAINER_SA_EMAIL" \
  --member="serviceAccount:${APPSPOT_SA}" \
  --role="roles/iam.serviceAccountUser" \
  --project "$PROJECT_ID" \
  --condition=None \
  --quiet >/dev/null

"$GCLOUD_BIN" artifacts repositories add-iam-policy-binding "$REPOSITORY" \
  --location "$REGION" \
  --member="serviceAccount:${TRAINER_SA_EMAIL}" \
  --role="roles/artifactregistry.reader" \
  --project "$PROJECT_ID" \
  --condition=None \
  --quiet >/dev/null

"$GCLOUD_BIN" artifacts repositories add-iam-policy-binding "$REPOSITORY" \
  --location "$REGION" \
  --member="serviceAccount:${VERTEX_SERVICE_AGENT}" \
  --role="roles/artifactregistry.reader" \
  --project "$PROJECT_ID" \
  --condition=None \
  --quiet >/dev/null

"$GCLOUD_BIN" artifacts repositories add-iam-policy-binding "$REPOSITORY" \
  --location "$REGION" \
  --member="serviceAccount:${CLOUDBUILD_SA}" \
  --role="roles/artifactregistry.writer" \
  --project "$PROJECT_ID" \
  --condition=None \
  --quiet >/dev/null || true

"$GCLOUD_BIN" artifacts repositories add-iam-policy-binding "$REPOSITORY" \
  --location "$REGION" \
  --member="serviceAccount:${COMPUTE_DEFAULT_SA}" \
  --role="roles/artifactregistry.writer" \
  --project "$PROJECT_ID" \
  --condition=None \
  --quiet >/dev/null || true

if ! "$GCLOUD_BIN" artifacts docker images describe "$BASE_IMAGE_URI" \
  --project "$PROJECT_ID" >/dev/null 2>&1; then
  echo "📦 Building training dependency base image for requirements hash ${REQUIREMENTS_HASH}"
  "$GCLOUD_BIN" builds submit back \
    --project "$PROJECT_ID" \
    --region "$REGION" \
    --config back/cloudbuild.vertex_training_base.yaml \
    --substitutions "_BASE_IMAGE_URI=${BASE_IMAGE_URI}" \
    --quiet
else
  echo "♻️ Reusing cached training dependency base image for requirements hash ${REQUIREMENTS_HASH}"
fi

"$GCLOUD_BIN" builds submit back \
  --project "$PROJECT_ID" \
  --region "$REGION" \
  --config back/cloudbuild.vertex_training.yaml \
  --substitutions "_IMAGE_URI=${IMAGE_URI},_BASE_IMAGE_URI=${BASE_IMAGE_URI}" \
  --quiet

echo "✅ Vertex training image deployed"
echo "   IMAGE_URI=${IMAGE_URI}"
echo "   BASE_IMAGE_URI=${BASE_IMAGE_URI}"
echo "   TRAINER_SA=${TRAINER_SA_EMAIL}"
echo "   STAGING_BUCKET=${STAGING_BUCKET}"
