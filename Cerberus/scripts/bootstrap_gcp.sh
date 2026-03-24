#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${1:-cerberus-9d94f}"
REGION="${2:-asia-east2}"

echo "Using project: ${PROJECT_ID}"
echo "Using region: ${REGION}"

gcloud config set project "${PROJECT_ID}"
gcloud config set run/region "${REGION}"

echo "Enabling required APIs..."
gcloud services enable \
  run.googleapis.com \
  container.googleapis.com \
  artifactregistry.googleapis.com \
  redis.googleapis.com \
  sqladmin.googleapis.com \
  secretmanager.googleapis.com \
  compute.googleapis.com \
  servicenetworking.googleapis.com \
  vpcaccess.googleapis.com \
  firebase.googleapis.com \
  firestore.googleapis.com \
  identitytoolkit.googleapis.com \
  cloudfunctions.googleapis.com \
  firebasehosting.googleapis.com \
  firebasestorage.googleapis.com \
  --project "${PROJECT_ID}"

echo "Bootstrap completed."
