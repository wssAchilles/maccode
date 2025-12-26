#!/bin/bash
# =============================================================================
# SentinEL Redis 基础设施脚本
# 创建 VPC 连接器和 Memorystore Redis 实例
# =============================================================================

set -e

# 配置项
PROJECT_ID="sentinel-ai-project-482208"
REGION="us-central1"
VPC_CONNECTOR_NAME="sentinel-connector"
VPC_CONNECTOR_RANGE="10.8.0.0/28"
REDIS_INSTANCE_NAME="sentinel-cache"
REDIS_MEMORY_SIZE_GB=1
REDIS_TIER="BASIC"  # BASIC (开发) 或 STANDARD_HA (生产高可用)

echo "============================================"
echo "   SentinEL Redis 基础设施配置"
echo "============================================"
echo ""

# 设置项目
echo "[INFO] 设置 GCP 项目: $PROJECT_ID"
gcloud config set project $PROJECT_ID

# 1. 启用必要的 API
echo ""
echo ">>> Step 1: 启用必要的 API"
gcloud services enable redis.googleapis.com --quiet
echo "[SUCCESS] redis.googleapis.com 已启用"

gcloud services enable vpcaccess.googleapis.com --quiet
echo "[SUCCESS] vpcaccess.googleapis.com 已启用"

gcloud services enable servicenetworking.googleapis.com --quiet
echo "[SUCCESS] servicenetworking.googleapis.com 已启用"

# 2. 创建 VPC 连接器
echo ""
echo ">>> Step 2: 创建 Serverless VPC Access 连接器"
if gcloud compute networks vpc-access connectors describe $VPC_CONNECTOR_NAME --region=$REGION &>/dev/null; then
    echo "[SKIP] VPC 连接器 '$VPC_CONNECTOR_NAME' 已存在"
else
    gcloud compute networks vpc-access connectors create $VPC_CONNECTOR_NAME \
        --region=$REGION \
        --range=$VPC_CONNECTOR_RANGE \
        --network=default \
        --min-instances=2 \
        --max-instances=3 \
        --quiet
    echo "[SUCCESS] 创建 VPC 连接器: $VPC_CONNECTOR_NAME"
fi

# 3. 创建 Redis 实例
echo ""
echo ">>> Step 3: 创建 Memorystore Redis 实例"
if gcloud redis instances describe $REDIS_INSTANCE_NAME --region=$REGION &>/dev/null; then
    echo "[SKIP] Redis 实例 '$REDIS_INSTANCE_NAME' 已存在"
else
    echo "[INFO] 正在创建 Redis 实例 (可能需要 5-10 分钟)..."
    gcloud redis instances create $REDIS_INSTANCE_NAME \
        --region=$REGION \
        --size=$REDIS_MEMORY_SIZE_GB \
        --tier=$REDIS_TIER \
        --network=default \
        --redis-version=redis_7_0 \
        --quiet
    echo "[SUCCESS] 创建 Redis 实例: $REDIS_INSTANCE_NAME"
fi

# 4. 获取 Redis 主机信息
echo ""
echo ">>> Step 4: 获取 Redis 连接信息"
REDIS_HOST=$(gcloud redis instances describe $REDIS_INSTANCE_NAME \
    --region=$REGION \
    --format='value(host)')
REDIS_PORT=$(gcloud redis instances describe $REDIS_INSTANCE_NAME \
    --region=$REGION \
    --format='value(port)')

if [ -z "$REDIS_HOST" ]; then
    echo "[ERROR] 无法获取 Redis 主机地址"
    exit 1
fi

# 5. 输出摘要
echo ""
echo "============================================"
echo "🎉 Redis 基础设施配置完成!"
echo "============================================"
echo ""
echo "VPC 连接器:"
echo "  名称:      $VPC_CONNECTOR_NAME"
echo "  区域:      $REGION"
echo "  IP 范围:   $VPC_CONNECTOR_RANGE"
echo ""
echo "Redis 实例:"
echo "  名称:      $REDIS_INSTANCE_NAME"
echo "  主机:      $REDIS_HOST"
echo "  端口:      $REDIS_PORT"
echo "  Tier:      $REDIS_TIER"
echo "  内存:      ${REDIS_MEMORY_SIZE_GB}GB"
echo ""
echo "部署时使用:"
echo "  --vpc-connector projects/$PROJECT_ID/locations/$REGION/connectors/$VPC_CONNECTOR_NAME"
echo "  --set-env-vars REDIS_HOST=$REDIS_HOST,REDIS_PORT=$REDIS_PORT"
echo ""
echo "============================================"
