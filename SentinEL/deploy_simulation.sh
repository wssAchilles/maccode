#!/bin/bash
# ============================================
# SentinEL Traffic Simulator 部署脚本
# 
# 功能: 构建并部署负载生成器到 Cloud Run Jobs
# ============================================

set -e  # 遇到错误立即退出

# ============================================
# 配置变量
# ============================================
PROJECT_ID="sentinel-ai-project-482208"
REGION="us-central1"
JOB_NAME="traffic-sim-job"
IMAGE_NAME="gcr.io/${PROJECT_ID}/traffic-sim"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

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

# ============================================
# 主流程
# ============================================
echo ""
echo -e "${BOLD}============================================${NC}"
echo -e "${BOLD}   SentinEL Traffic Simulator 部署${NC}"
echo -e "${BOLD}============================================${NC}"
echo ""

# Step 1: 设置项目
log_info "设置 GCP 项目: ${PROJECT_ID}"
gcloud config set project ${PROJECT_ID}

# Step 2: 构建镜像
log_info "构建 Docker 镜像..."
cd simulation
gcloud builds submit --tag ${IMAGE_NAME} --quiet

log_success "镜像构建完成: ${IMAGE_NAME}"
cd ..

# Step 3: 删除已有作业 (如果存在)
log_info "检查已有作业..."
if gcloud run jobs describe ${JOB_NAME} --region ${REGION} &>/dev/null; then
    log_warn "删除已有作业: ${JOB_NAME}"
    gcloud run jobs delete ${JOB_NAME} --region ${REGION} --quiet
fi

# Step 4: 创建 Cloud Run Job
log_info "创建 Cloud Run Job..."
gcloud run jobs create ${JOB_NAME} \
    --image ${IMAGE_NAME} \
    --region ${REGION} \
    --task-timeout 3600 \
    --max-retries 0 \
    --quiet

log_success "Job 创建完成: ${JOB_NAME}"

# Step 5: 提示如何运行
echo ""
echo -e "${BOLD}============================================${NC}"
echo -e "${GREEN}${BOLD}🚀 Traffic Simulator 部署完成!${NC}"
echo -e "${BOLD}============================================${NC}"
echo ""
echo -e "运行作业:"
echo -e "  ${YELLOW}gcloud run jobs execute ${JOB_NAME} --region ${REGION}${NC}"
echo ""
echo -e "查看日志:"
echo -e "  ${YELLOW}gcloud run jobs executions logs ${JOB_NAME} --region ${REGION}${NC}"
echo ""
echo -e "停止作业 (如需):"
echo -e "  ${YELLOW}gcloud run jobs executions list --job ${JOB_NAME} --region ${REGION}${NC}"
echo -e "  ${YELLOW}gcloud run jobs executions cancel <EXECUTION_NAME> --region ${REGION}${NC}"
echo ""
echo -e "${BOLD}============================================${NC}"
