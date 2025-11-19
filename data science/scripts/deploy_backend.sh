#!/bin/bash

# ===================================
# GAE 后端部署脚本
# ===================================

set -e  # 遇到错误立即退出

echo "🚀 开始部署后端到 Google App Engine..."

# 检查是否在正确的目录
if [ ! -f "app.yaml" ]; then
    echo "❌ 错误: 请在 back/ 目录下运行此脚本"
    exit 1
fi

# 检查是否安装 gcloud
if ! command -v gcloud &> /dev/null; then
    echo "❌ 错误: 未安装 gcloud CLI"
    echo "请访问: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# 检查依赖文件
if [ ! -f "requirements.txt" ]; then
    echo "❌ 错误: 未找到 requirements.txt"
    exit 1
fi

# 确认部署
echo "📋 即将部署到 GAE..."
gcloud config get-value project
read -p "确认部署? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ 部署已取消"
    exit 0
fi

# 执行部署
echo "📦 正在部署..."
gcloud app deploy --quiet

# 获取部署后的 URL
echo "✅ 部署成功!"
echo "🌐 应用 URL:"
gcloud app browse --no-launch-browser

echo "📊 查看日志:"
echo "gcloud app logs tail -s default"
