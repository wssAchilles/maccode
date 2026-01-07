#!/bin/bash

# ===================================
# Cloud Run Backend Deployment Script
# Optimized for "Dual-Core" Architecture (On-Demand High Performance)
# Cost Strategy: Min Instances = 0 (Pay only when used)
# ===================================

set -e  # Exit immediately if a command exits with a non-zero status.

echo "🚀 Starting Cloud Run Deployment Sequence..."

# 1. Project Setup
PROJECT_ID=$(gcloud config get-value project)
echo "✅ Project ID: $PROJECT_ID"

if [ -z "$PROJECT_ID" ]; then
    echo "❌ Error: Could not determine Google Cloud Project ID."
    echo "Please run 'gcloud config set project <YOUR_PROJECT_ID>' first."
    exit 1
fi

SERVICE_NAME="sentinel-backend-cloudrun"
REGION="us-central1" # Or allow user to override

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

gcloud builds submit "$BUILD_CONTEXT" \
    --tag "gcr.io/$PROJECT_ID/$SERVICE_NAME" \
    --quiet

echo "✅ Build Successful."

# 3. Deploy to Cloud Run
echo "📦 Deploying to Cloud Run..."
echo "   Configuration: 4Gi Memory, 2 vCPU, Min Instances 0 (Cost Saving)"

gcloud run deploy "$SERVICE_NAME" \
    --image "gcr.io/$PROJECT_ID/$SERVICE_NAME" \
    --platform managed \
    --region "$REGION" \
    --allow-unauthenticated \
    --memory 4Gi \
    --cpu 2 \
    --timeout 300 \
    --concurrency 8 \
    --min-instances 0 \
    --max-instances 3 \
    --quiet

# 4. Success Output
echo "✅ Deployment Complete!"
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --platform managed --region $REGION --format 'value(status.url)')
echo "🌐 Service URL: $SERVICE_URL"
echo ""
echo "👉 Next Step: Update your Frontend configuration with this URL."
