#!/bin/bash
set -e

REGION="us-central1"
PROJECT_ID="sentinel-ai-project-482208"
IMAGE_URI="gcr.io/$PROJECT_ID/sentinel-serve:latest"
MODEL_DISPLAY_NAME="sentinel-churn-transformer-v2"
ENDPOINT_ID="8203956532627374080" # sentinel-churn-transformer

echo "========================================================"
echo "开始部署流程 (Attempt 2)"
echo "Region: $REGION"
echo "Image: $IMAGE_URI"
echo "Target Endpoint: $ENDPOINT_ID"
echo "========================================================"
echo "========================================================"
echo "[0/2] 构建 Docker 镜像..."
# 必须使用项目根目录作为构建上下文，因为 Dockerfile.serve 中使用了 ml_engine/ 前缀
cp ml_engine/Dockerfile.serve ./Dockerfile
gcloud builds submit . --tag "${IMAGE_URI}" --project=$PROJECT_ID
rm ./Dockerfile

echo "[1/2] 上传模型到 Vertex AI Model Registry..."
gcloud ai models upload \
  --region=$REGION \
  --display-name=$MODEL_DISPLAY_NAME \
  --container-image-uri=$IMAGE_URI \
  --container-ports=8080 \
  --container-predict-route="/predict" \
  --container-health-route="/health" \
  --project=$PROJECT_ID

# 获取最新上传的模型 ID
MODEL_NAME=$(gcloud ai models list \
  --region=$REGION \
  --filter="display_name=$MODEL_DISPLAY_NAME" \
  --format="value(name)" \
  --limit=1 \
  --sort-by="~createTime")

if [ -z "$MODEL_NAME" ]; then
    echo "❌ 获取模型 ID 失败"
    exit 1
fi

echo "✅ 模型已上传: $MODEL_NAME"

echo "[2/2] 部署模型到 Endpoint..."
# 注意: deploy-model 是同步命令，不使用 --async 以确保能看到错误
# gcloud ai endpoints deploy-model 不支持 --async 参数 (部分版本)
# 我们让它在前台运行，直到完成或失败
gcloud ai endpoints deploy-model $ENDPOINT_ID \
  --region=$REGION \
  --model=$MODEL_NAME \
  --display-name="deployed-transformer-local-hpt" \
  --machine-type="n1-standard-2" \
  --min-replica-count=1 \
  --max-replica-count=1 \
  --traffic-split="0=100" \
  --project=$PROJECT_ID

echo "========================================================"
echo "🚀 部署操作已完成!"
echo "========================================================"
