#!/bin/bash
# ============================================
# SentinEL-Pro 一键部署脚本
# 
# 功能: 自动化构建并部署前后端到 Google Cloud Run
# 作者: Google Cloud Principal DevOps Engineer
# ============================================

set -e  # 遇到错误立即退出

# ============================================
# 配置变量
# ============================================
PROJECT_ID="sentinel-ai-project-482208"
REGION="us-central1"
BACKEND_SERVICE_NAME="sentinel-backend"
FRONTEND_SERVICE_NAME="sentinel-frontend"
BACKEND_IMAGE="gcr.io/${PROJECT_ID}/${BACKEND_SERVICE_NAME}"
FRONTEND_IMAGE="gcr.io/${PROJECT_ID}/${FRONTEND_SERVICE_NAME}"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# ============================================
# 辅助函数
# ============================================
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_command() {
    if ! command -v $1 &> /dev/null; then
        log_error "$1 未安装，请先安装 Google Cloud SDK"
        exit 1
    fi
}

# ============================================
# 前置检查
# ============================================
echo ""
echo -e "${BOLD}============================================${NC}"
echo -e "${BOLD}   SentinEL-Pro Cloud Run 部署脚本${NC}"
echo -e "${BOLD}============================================${NC}"
echo ""

log_info "检查必要工具..."
check_command gcloud
check_command docker

log_info "设置 GCP 项目: ${PROJECT_ID}"
gcloud config set project ${PROJECT_ID}

log_info "启用必要的 API..."
gcloud services enable cloudbuild.googleapis.com run.googleapis.com containerregistry.googleapis.com --quiet

# ============================================
# Step 1: 构建并部署后端
# ============================================
echo ""
echo -e "${BOLD}>>> Step 1: 构建并部署后端服务 <<<${NC}"
echo ""

log_info "构建后端 Docker 镜像..."
cd backend
gcloud builds submit --tag ${BACKEND_IMAGE} --quiet

# 获取 Redis IP (如果存在)
log_info "检查 Redis 实例..."
REDIS_HOST=$(gcloud redis instances describe sentinel-cache --region=${REGION} --format='value(host)' 2>/dev/null || echo "")
VPC_CONNECTOR_FLAG=""
REDIS_ENV_FLAG=""

if [ -n "$REDIS_HOST" ]; then
    log_success "检测到 Redis 实例: $REDIS_HOST"
    VPC_CONNECTOR_FLAG="--vpc-connector=sentinel-connector"
    REDIS_ENV_FLAG="--set-env-vars=REDIS_HOST=${REDIS_HOST},REDIS_PORT=6379"
else
    log_warn "未检测到 Redis 实例，将以无缓存模式部署"
fi

log_info "部署后端到 Cloud Run..."
gcloud run deploy ${BACKEND_SERVICE_NAME} \
    --image ${BACKEND_IMAGE} \
    --region ${REGION} \
    --platform managed \
    --allow-unauthenticated \
    --memory 1Gi \
    --cpu 1 \
    --min-instances 0 \
    --max-instances 10 \
    ${VPC_CONNECTOR_FLAG} \
    ${REDIS_ENV_FLAG} \
    --quiet

log_success "后端部署完成!"
cd ..

# ============================================
# Step 2: 获取后端 URL
# ============================================
echo ""
echo -e "${BOLD}>>> Step 2: 获取后端服务 URL <<<${NC}"
echo ""

log_info "正在获取后端 URL..."
BACKEND_URL=$(gcloud run services describe ${BACKEND_SERVICE_NAME} \
    --region ${REGION} \
    --platform managed \
    --format 'value(status.url)')

if [ -z "$BACKEND_URL" ]; then
    log_error "无法获取后端 URL，部署可能失败"
    exit 1
fi

log_success "后端 URL: ${BACKEND_URL}"

# ============================================
# Step 3: 构建并部署前端
# ============================================
echo ""
echo -e "${BOLD}>>> Step 3: 构建并部署前端服务 <<<${NC}"
echo ""

log_info "构建前端 Docker 镜像 (注入 API URL: ${BACKEND_URL})..."
cd frontend

# 关键: 使用 cloudbuild.yaml 配置文件传递构建参数
# gcloud builds submit 不支持 --build-arg，必须通过 --substitutions 传递
gcloud builds submit \
    --config cloudbuild.yaml \
    --substitutions _API_URL=${BACKEND_URL} \
    --quiet

log_info "部署前端到 Cloud Run..."
gcloud run deploy ${FRONTEND_SERVICE_NAME} \
    --image ${FRONTEND_IMAGE} \
    --region ${REGION} \
    --platform managed \
    --allow-unauthenticated \
    --memory 512Mi \
    --cpu 1 \
    --min-instances 0 \
    --max-instances 10 \
    --quiet

log_success "前端部署完成!"
cd ..

# ============================================
# Step 4: 获取并显示最终结果
# ============================================
echo ""
echo -e "${BOLD}>>> Step 4: 部署摘要 <<<${NC}"
echo ""

FRONTEND_URL=$(gcloud run services describe ${FRONTEND_SERVICE_NAME} \
    --region ${REGION} \
    --platform managed \
    --format 'value(status.url)')

echo ""
echo -e "${BOLD}============================================${NC}"
echo -e "${GREEN}${BOLD}🚀 Deployment Complete!${NC}"
echo -e "${BOLD}============================================${NC}"
echo ""
echo -e "后端服务 (Backend):  ${BACKEND_URL}"
echo -e "前端服务 (Frontend): ${GREEN}${BOLD}${FRONTEND_URL}${NC}"
echo ""
echo -e "Swagger API 文档:    ${BACKEND_URL}/docs"
echo -e "Dashboard:           ${FRONTEND_URL}/dashboard"
echo ""
echo -e "${BOLD}============================================${NC}"
