#!/bin/bash

# ===================================
# Firebase Hosting 前端部署脚本
# ===================================

set -e  # 遇到错误立即退出

FLUTTER_BIN="${FLUTTER_BIN:-}"
if [ -z "$FLUTTER_BIN" ]; then
    if command -v flutter >/dev/null 2>&1; then
        FLUTTER_BIN="$(command -v flutter)"
    elif [ -x "/Users/achilles/development/flutter/bin/flutter" ]; then
        FLUTTER_BIN="/Users/achilles/development/flutter/bin/flutter"
    else
        echo "❌ 错误: 未安装 Flutter"
        exit 1
    fi
fi

FIREBASE_BIN="${FIREBASE_BIN:-}"
if [ -z "$FIREBASE_BIN" ]; then
    if command -v firebase >/dev/null 2>&1; then
        FIREBASE_BIN="$(command -v firebase)"
    elif [ -x "/Users/achilles/.nvm/versions/node/v24.11.0/bin/firebase" ]; then
        FIREBASE_BIN="/Users/achilles/.nvm/versions/node/v24.11.0/bin/firebase"
    elif [ -x "/Users/achilles/.nvm/versions/node/v22.21.1/bin/firebase" ]; then
        FIREBASE_BIN="/Users/achilles/.nvm/versions/node/v22.21.1/bin/firebase"
    else
        echo "❌ 错误: 未安装 Firebase CLI"
        exit 1
    fi
fi

NODE_BIN_DIR="$(dirname "$FIREBASE_BIN")"
if [ -x "$NODE_BIN_DIR/node" ]; then
    export PATH="$NODE_BIN_DIR:$PATH"
fi

echo "🚀 开始部署前端到 Firebase Hosting..."

# 检查是否在正确的目录
if [ -f "pubspec.yaml" ]; then
    FRONTEND_DIR="$(pwd)"
elif [ -f "front/pubspec.yaml" ]; then
    FRONTEND_DIR="$(pwd)/front"
else
    echo "❌ 错误: 未找到 front/pubspec.yaml"
    exit 1
fi

cd "$FRONTEND_DIR"

# 确认部署
echo "📋 即将部署到 Firebase Hosting..."
if [ "${AUTO_CONFIRM:-false}" != "true" ]; then
    read -p "确认部署? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ 部署已取消"
        exit 0
    fi
fi

# 安装依赖
echo "📦 安装依赖..."
"$FLUTTER_BIN" pub get

# 构建 Web 版本
echo "🔨 构建 Web 应用..."
"$FLUTTER_BIN" build web --release

# 部署到 Firebase
echo "🚀 部署到 Firebase Hosting..."
"$FIREBASE_BIN" deploy --only hosting

echo "✅ 部署成功!"
echo "🌐 访问你的应用: https://data-science-44398.web.app"
echo "ℹ️ 如需查看 Firebase 控制台，请手动访问: https://console.firebase.google.com/project/data-science-44398/overview"
