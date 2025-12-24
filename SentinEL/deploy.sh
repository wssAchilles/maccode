#!/bin/bash

# =============================================================================
# Cloud Run 部署脚本
# 服务名称: sentinel-agent-service
# 区域: us-central1
# =============================================================================

set -e  # 遇到错误立即退出

echo "🚀 开始部署 Sentinel Agent 到 Cloud Run..."

# 使用 --source . 让 Cloud Build 在云端构建容器镜像
# 这样本地不需要安装 Docker
gcloud run deploy sentinel-agent-service \
    --source . \
    --region us-central1 \
    --allow-unauthenticated \
    --platform managed

echo "✅ 部署完成！"
echo "📍 服务 URL 已在上方输出，可以直接在浏览器中访问测试。"
