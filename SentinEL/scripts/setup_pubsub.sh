#!/bin/bash
# =============================================================================
# SentinEL Pub/Sub 基础设施脚本
# 创建用于异步分析任务的 Topic, Subscription 和 Dead Letter Queue
# =============================================================================

set -e

# 配置项
PROJECT_ID="sentinel-ai-project-482208"
REGION="us-central1"
BACKEND_URL="https://sentinel-backend-kijag7ukkq-uc.a.run.app"

# 资源名称
TOPIC_NAME="sentinel-analysis-trigger"
SUBSCRIPTION_NAME="sentinel-analysis-worker"
DLQ_TOPIC_NAME="sentinel-analysis-dlq"
DLQ_SUBSCRIPTION_NAME="sentinel-analysis-dlq-sub"

echo "============================================"
echo "   SentinEL Pub/Sub 基础设施配置"
echo "============================================"
echo ""

# 设置项目
echo "[INFO] 设置 GCP 项目: $PROJECT_ID"
gcloud config set project $PROJECT_ID

# 1. 创建 Dead Letter Queue Topic (先创建，因为主 Subscription 依赖它)
echo ""
echo ">>> Step 1: 创建 Dead Letter Queue Topic"
if gcloud pubsub topics describe $DLQ_TOPIC_NAME &>/dev/null; then
    echo "[SKIP] DLQ Topic '$DLQ_TOPIC_NAME' 已存在"
else
    gcloud pubsub topics create $DLQ_TOPIC_NAME
    echo "[SUCCESS] 创建 DLQ Topic: $DLQ_TOPIC_NAME"
fi

# 2. 创建 DLQ Subscription (用于后续人工处理失败消息)
echo ""
echo ">>> Step 2: 创建 Dead Letter Queue Subscription"
if gcloud pubsub subscriptions describe $DLQ_SUBSCRIPTION_NAME &>/dev/null; then
    echo "[SKIP] DLQ Subscription '$DLQ_SUBSCRIPTION_NAME' 已存在"
else
    gcloud pubsub subscriptions create $DLQ_SUBSCRIPTION_NAME \
        --topic=$DLQ_TOPIC_NAME \
        --ack-deadline=60
    echo "[SUCCESS] 创建 DLQ Subscription: $DLQ_SUBSCRIPTION_NAME"
fi

# 3. 创建主 Topic
echo ""
echo ">>> Step 3: 创建分析触发 Topic"
if gcloud pubsub topics describe $TOPIC_NAME &>/dev/null; then
    echo "[SKIP] Topic '$TOPIC_NAME' 已存在"
else
    gcloud pubsub topics create $TOPIC_NAME
    echo "[SUCCESS] 创建 Topic: $TOPIC_NAME"
fi

# 4. 获取当前项目编号 (用于服务账号配置)
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
PUBSUB_SERVICE_ACCOUNT="service-${PROJECT_NUMBER}@gcp-sa-pubsub.iam.gserviceaccount.com"

# 5. 授予 Pub/Sub 服务账号调用 Cloud Run 的权限
echo ""
echo ">>> Step 4: 配置 IAM 权限 (允许 Pub/Sub 调用 Cloud Run)"
gcloud run services add-iam-policy-binding sentinel-backend \
    --region=$REGION \
    --member="serviceAccount:${PUBSUB_SERVICE_ACCOUNT}" \
    --role="roles/run.invoker" \
    --quiet

echo "[SUCCESS] 已授予 Pub/Sub 服务账号 Cloud Run 调用权限"

# 6. 创建 Push Subscription (指向 Cloud Run 端点)
echo ""
echo ">>> Step 5: 创建 Push Subscription"
PUSH_ENDPOINT="${BACKEND_URL}/api/v1/events/process"

if gcloud pubsub subscriptions describe $SUBSCRIPTION_NAME &>/dev/null; then
    echo "[SKIP] Subscription '$SUBSCRIPTION_NAME' 已存在"
    echo "[INFO] 更新 Push 端点..."
    gcloud pubsub subscriptions update $SUBSCRIPTION_NAME \
        --push-endpoint=$PUSH_ENDPOINT \
        --push-auth-service-account="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
else
    gcloud pubsub subscriptions create $SUBSCRIPTION_NAME \
        --topic=$TOPIC_NAME \
        --push-endpoint=$PUSH_ENDPOINT \
        --push-auth-service-account="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
        --ack-deadline=120 \
        --dead-letter-topic=$DLQ_TOPIC_NAME \
        --max-delivery-attempts=5 \
        --min-retry-delay=10s \
        --max-retry-delay=600s
    echo "[SUCCESS] 创建 Push Subscription: $SUBSCRIPTION_NAME"
fi

# 7. 授予 Pub/Sub 发布 DLQ 消息的权限
echo ""
echo ">>> Step 6: 配置 DLQ 发布权限"
gcloud pubsub topics add-iam-policy-binding $DLQ_TOPIC_NAME \
    --member="serviceAccount:${PUBSUB_SERVICE_ACCOUNT}" \
    --role="roles/pubsub.publisher" \
    --quiet

gcloud pubsub subscriptions add-iam-policy-binding $SUBSCRIPTION_NAME \
    --member="serviceAccount:${PUBSUB_SERVICE_ACCOUNT}" \
    --role="roles/pubsub.subscriber" \
    --quiet

echo "[SUCCESS] DLQ 权限配置完成"

# 8. 输出摘要
echo ""
echo "============================================"
echo "🎉 Pub/Sub 基础设施配置完成!"
echo "============================================"
echo ""
echo "Topic:          $TOPIC_NAME"
echo "Subscription:   $SUBSCRIPTION_NAME"
echo "Push Endpoint:  $PUSH_ENDPOINT"
echo "DLQ Topic:      $DLQ_TOPIC_NAME"
echo ""
echo "测试命令:"
echo "  gcloud pubsub topics publish $TOPIC_NAME --message='{\"user_id\":\"test\",\"analysis_id\":\"test-123\"}'"
echo ""
