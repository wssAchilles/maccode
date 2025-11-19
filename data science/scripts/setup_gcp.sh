#!/bin/bash

# ===================================
# GCP 项目初始化脚本
# ===================================

set -e  # 遇到错误立即退出

echo "🔧 开始初始化 GCP 项目..."

# 检查是否安装 gcloud
if ! command -v gcloud &> /dev/null; then
    echo "❌ 错误: 未安装 gcloud CLI"
    echo "请访问: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# 登录
echo "🔐 登录 GCP..."
gcloud auth login

# 选择或创建项目
echo "📋 请输入项目 ID (或留空创建新项目):"
read -r PROJECT_ID

if [ -z "$PROJECT_ID" ]; then
    echo "创建新项目..."
    read -p "请输入新项目 ID: " NEW_PROJECT_ID
    gcloud projects create "$NEW_PROJECT_ID"
    PROJECT_ID=$NEW_PROJECT_ID
fi

# 设置当前项目
echo "⚙️  设置项目: $PROJECT_ID"
gcloud config set project "$PROJECT_ID"

# 启用必要的 API
echo "🔌 启用必要的 Google Cloud API..."
gcloud services enable appengine.googleapis.com
gcloud services enable storage.googleapis.com
gcloud services enable cloudresourcemanager.googleapis.com
gcloud services enable firebase.googleapis.com

# 创建 App Engine 应用
echo "📱 创建 App Engine 应用..."
read -p "请选择区域 (例如: us-central): " REGION
gcloud app create --region="$REGION" || echo "App Engine 应用已存在"

# 创建 Cloud Storage 存储桶
echo "🗄️  创建 Cloud Storage 存储桶..."
BUCKET_NAME="${PROJECT_ID}-data-science"
gsutil mb -p "$PROJECT_ID" gs://"$BUCKET_NAME" || echo "存储桶已存在"

# 设置存储桶权限
echo "🔒 设置存储桶权限..."
gsutil iam ch allUsers:objectViewer gs://"$BUCKET_NAME" || true

echo "✅ GCP 项目初始化完成!"
echo ""
echo "📝 项目信息:"
echo "  项目 ID: $PROJECT_ID"
echo "  区域: $REGION"
echo "  存储桶: gs://$BUCKET_NAME"
echo ""
echo "🎉 下一步:"
echo "  1. 在 Firebase Console 中添加 Web 应用"
echo "  2. 配置 .env 文件"
echo "  3. 运行 deploy_backend.sh 部署后端"
echo "  4. 运行 deploy_frontend.sh 部署前端"
