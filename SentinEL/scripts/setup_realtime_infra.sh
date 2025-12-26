#!/usr/bin/env bash
# =============================================================================
# SentinEL 实时数据管道基础设施部署脚本
# 
# 功能:
#   1. 创建 Pub/Sub Topic & Subscription (sentinel-clickstream-topic)
#   2. 创建 Vertex AI Feature Store Online Store
#   3. 定义 Feature Group 和 Feature View
#
# 使用方法:
#   chmod +x scripts/setup_realtime_infra.sh
#   ./scripts/setup_realtime_infra.sh
#
# 前置条件:
#   - gcloud CLI 已安装并认证
#   - 项目已启用 Pub/Sub, Vertex AI, BigQuery APIs
# =============================================================================

set -euo pipefail

# =============================================================================
# 配置变量
# =============================================================================
PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-sentinel-ai-project-482208}"
REGION="us-central1"

# Pub/Sub 配置
PUBSUB_TOPIC="sentinel-clickstream-topic"
PUBSUB_SUBSCRIPTION="sentinel-clickstream-sub"

# Feature Store 配置
FEATURE_ONLINE_STORE="sentinel-online-store"
FEATURE_GROUP="user_realtime_features"
BQ_DATASET="sentinel_features"
BQ_TABLE="user_realtime_aggregates"

# =============================================================================
# 辅助函数
# =============================================================================
log_info() {
    echo -e "\033[0;32m[INFO]\033[0m $1"
}

log_warn() {
    echo -e "\033[0;33m[WARN]\033[0m $1"
}

log_error() {
    echo -e "\033[0;31m[ERROR]\033[0m $1"
}

check_command() {
    if ! command -v "$1" &> /dev/null; then
        log_error "$1 未安装，请先安装"
        exit 1
    fi
}

# =============================================================================
# Step 1: 启用必要的 API
# =============================================================================
enable_apis() {
    log_info "启用必要的 Google Cloud APIs..."
    
    gcloud services enable pubsub.googleapis.com --project="$PROJECT_ID" --quiet || true
    gcloud services enable aiplatform.googleapis.com --project="$PROJECT_ID" --quiet || true
    gcloud services enable dataflow.googleapis.com --project="$PROJECT_ID" --quiet || true
    gcloud services enable bigquery.googleapis.com --project="$PROJECT_ID" --quiet || true
    
    log_info "APIs 已启用"
}

# =============================================================================
# Step 2: 创建 Pub/Sub Topic 和 Subscription
# =============================================================================
setup_pubsub() {
    log_info "设置 Pub/Sub Topic 和 Subscription..."
    
    # 创建 Topic (如果不存在)
    if gcloud pubsub topics describe "$PUBSUB_TOPIC" --project="$PROJECT_ID" &> /dev/null; then
        log_warn "Topic $PUBSUB_TOPIC 已存在，跳过创建"
    else
        gcloud pubsub topics create "$PUBSUB_TOPIC" \
            --project="$PROJECT_ID" \
            --labels="env=production,app=sentinel"
        log_info "Topic $PUBSUB_TOPIC 创建成功"
    fi
    
    # 创建 Subscription (如果不存在)
    if gcloud pubsub subscriptions describe "$PUBSUB_SUBSCRIPTION" --project="$PROJECT_ID" &> /dev/null; then
        log_warn "Subscription $PUBSUB_SUBSCRIPTION 已存在，跳过创建"
    else
        gcloud pubsub subscriptions create "$PUBSUB_SUBSCRIPTION" \
            --topic="$PUBSUB_TOPIC" \
            --project="$PROJECT_ID" \
            --ack-deadline=60 \
            --message-retention-duration=1h \
            --labels="env=production,app=sentinel"
        log_info "Subscription $PUBSUB_SUBSCRIPTION 创建成功"
    fi
}

# =============================================================================
# Step 3: 创建 BigQuery Dataset 用于 Feature Store 数据源
# =============================================================================
setup_bigquery() {
    log_info "设置 BigQuery Dataset 作为 Feature Store 数据源..."
    
    # 创建 Dataset (如果不存在)
    if bq show --project_id="$PROJECT_ID" "$BQ_DATASET" &> /dev/null; then
        log_warn "Dataset $BQ_DATASET 已存在，跳过创建"
    else
        bq mk --project_id="$PROJECT_ID" \
            --location="$REGION" \
            --dataset "$BQ_DATASET"
        log_info "Dataset $BQ_DATASET 创建成功"
    fi
    
    # 创建实时特征聚合表
    log_info "创建实时特征聚合表..."
    bq query --project_id="$PROJECT_ID" --use_legacy_sql=false \
        "CREATE TABLE IF NOT EXISTS \`$PROJECT_ID.$BQ_DATASET.$BQ_TABLE\` (
            entity_id STRING NOT NULL,
            feature_timestamp TIMESTAMP NOT NULL,
            realtime_clicks_5m INT64,
            rage_clicks_5m INT64,
            policy_views_5m INT64,
            cart_additions_5m INT64,
            active_session_duration FLOAT64,
            last_event_timestamp TIMESTAMP
        )
        PARTITION BY DATE(feature_timestamp)
        CLUSTER BY entity_id
        OPTIONS (
            description='SentinEL 实时用户特征聚合表',
            labels=[('app', 'sentinel'), ('type', 'features')]
        )"
    
    log_info "BigQuery 表 $BQ_TABLE 创建成功"
}

# =============================================================================
# Step 4: 创建 Vertex AI Feature Store (Online Store)
# =============================================================================
setup_feature_store() {
    log_info "设置 Vertex AI Feature Store Online Store..."
    
    # 使用 REST API 创建 Feature Online Store
    # 检查是否已存在
    STORE_EXISTS=$(gcloud ai feature-online-stores list \
        --project="$PROJECT_ID" \
        --region="$REGION" \
        --format="value(name)" \
        --filter="name~$FEATURE_ONLINE_STORE" 2>/dev/null || echo "")
    
    if [ -n "$STORE_EXISTS" ]; then
        log_warn "Feature Online Store $FEATURE_ONLINE_STORE 已存在，跳过创建"
    else
        log_info "创建 Feature Online Store (Bigtable 优化模式)..."
        
        # 使用 gcloud 创建 Feature Online Store
        gcloud ai feature-online-stores create "$FEATURE_ONLINE_STORE" \
            --project="$PROJECT_ID" \
            --region="$REGION" \
            --bigtable-auto-scaling \
            --bigtable-min-node-count=1 \
            --bigtable-max-node-count=3 \
            --bigtable-cpu-utilization-target=50 || {
            log_warn "Feature Online Store 创建可能需要几分钟..."
        }
        
        log_info "Feature Online Store $FEATURE_ONLINE_STORE 创建请求已提交"
    fi
}

# =============================================================================
# Step 5: 创建 Feature Group 和 Feature View
# =============================================================================
setup_feature_group() {
    log_info "设置 Feature Group..."
    
    # 检查 Feature Group 是否存在
    FG_EXISTS=$(gcloud ai feature-groups list \
        --project="$PROJECT_ID" \
        --region="$REGION" \
        --format="value(name)" \
        --filter="name~$FEATURE_GROUP" 2>/dev/null || echo "")
    
    if [ -n "$FG_EXISTS" ]; then
        log_warn "Feature Group $FEATURE_GROUP 已存在，跳过创建"
    else
        log_info "创建 Feature Group (关联 BigQuery 数据源)..."
        
        gcloud ai feature-groups create "$FEATURE_GROUP" \
            --project="$PROJECT_ID" \
            --region="$REGION" \
            --source="bq:///$PROJECT_ID.$BQ_DATASET.$BQ_TABLE" \
            --entity-id-columns=entity_id || {
            log_warn "Feature Group 创建可能需要几分钟..."
        }
        
        log_info "Feature Group $FEATURE_GROUP 创建请求已提交"
    fi
}

# =============================================================================
# Step 6: 创建 Feature View (Online Serving)
# =============================================================================
setup_feature_view() {
    log_info "设置 Feature View for Online Serving..."
    
    FEATURE_VIEW_NAME="user_realtime_view"
    
    # 检查 Feature View 是否存在
    FV_EXISTS=$(gcloud ai feature-views list \
        --project="$PROJECT_ID" \
        --region="$REGION" \
        --feature-online-store="$FEATURE_ONLINE_STORE" \
        --format="value(name)" \
        --filter="name~$FEATURE_VIEW_NAME" 2>/dev/null || echo "")
    
    if [ -n "$FV_EXISTS" ]; then
        log_warn "Feature View $FEATURE_VIEW_NAME 已存在，跳过创建"
    else
        log_info "创建 Feature View..."
        
        gcloud ai feature-views create "$FEATURE_VIEW_NAME" \
            --project="$PROJECT_ID" \
            --region="$REGION" \
            --feature-online-store="$FEATURE_ONLINE_STORE" \
            --feature-registry-source="projects/$PROJECT_ID/locations/$REGION/featureGroups/$FEATURE_GROUP/features/*" \
            --sync-config-cron="*/5 * * * *" || {
            log_warn "Feature View 创建可能需要几分钟..."
        }
        
        log_info "Feature View $FEATURE_VIEW_NAME 创建请求已提交"
    fi
}

# =============================================================================
# 主函数
# =============================================================================
main() {
    echo "============================================"
    echo "   SentinEL 实时数据管道基础设施部署"
    echo "============================================"
    echo ""
    echo "项目: $PROJECT_ID"
    echo "区域: $REGION"
    echo ""
    
    # 检查依赖
    check_command gcloud
    check_command bq
    
    # 设置项目
    gcloud config set project "$PROJECT_ID" --quiet
    
    # 执行部署步骤
    enable_apis
    setup_pubsub
    setup_bigquery
    setup_feature_store
    setup_feature_group
    setup_feature_view
    
    echo ""
    echo "============================================"
    echo "🚀 基础设施部署完成!"
    echo "============================================"
    echo ""
    echo "Pub/Sub Topic:       projects/$PROJECT_ID/topics/$PUBSUB_TOPIC"
    echo "Pub/Sub Subscription: projects/$PROJECT_ID/subscriptions/$PUBSUB_SUBSCRIPTION"
    echo "Feature Store:       projects/$PROJECT_ID/locations/$REGION/featureOnlineStores/$FEATURE_ONLINE_STORE"
    echo "Feature Group:       projects/$PROJECT_ID/locations/$REGION/featureGroups/$FEATURE_GROUP"
    echo ""
    echo "下一步: 运行 python simulation/live_traffic_gen.py 开始生成模拟流量"
}

# 执行主函数
main "$@"
