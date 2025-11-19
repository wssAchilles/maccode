#!/bin/bash

# ===================================
# Firebase Hosting 前端部署脚本
# ===================================

set -e  # 遇到错误立即退出

echo "🚀 开始部署前端到 Firebase Hosting..."

# 检查是否在正确的目录
if [ ! -f "pubspec.yaml" ]; then
    echo "❌ 错误: 请在 front/ 目录下运行此脚本"
    exit 1
fi

# 检查是否安装 Flutter
if ! command -v flutter &> /dev/null; then
    echo "❌ 错误: 未安装 Flutter"
    echo "请访问: https://flutter.dev/docs/get-started/install"
    exit 1
fi

# 检查是否安装 Firebase CLI
if ! command -v firebase &> /dev/null; then
    echo "❌ 错误: 未安装 Firebase CLI"
    echo "运行: npm install -g firebase-tools"
    exit 1
fi

# 确认部署
echo "📋 即将部署到 Firebase Hosting..."
read -p "确认部署? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ 部署已取消"
    exit 0
fi

# 安装依赖
echo "📦 安装依赖..."
flutter pub get

# 构建 Web 版本
echo "🔨 构建 Web 应用..."
flutter build web --release

# 部署到 Firebase
echo "🚀 部署到 Firebase Hosting..."
firebase deploy --only hosting

echo "✅ 部署成功!"
echo "🌐 访问你的应用:"
firebase open hosting:site
