#!/bin/bash

# ========================================
# Aether Docker 部署验证脚本
# 用于验证 Docker Compose 部署是否成功
# ========================================

set -e  # 遇到错误立即退出

echo "========================================="
echo "🚀 aether Docker 部署验证开始"
echo "========================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查 Docker 是否运行
echo "📦 检查 Docker..."
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker 未运行，请先启动 Docker${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Docker 正在运行${NC}"
echo ""

# 检查容器状态
echo "🐳 检查容器状态..."
if docker ps | grep -q "aether-api"; then
    echo -e "${GREEN}✅ aether-api 容器正在运行${NC}"
else
    echo -e "${RED}❌ aether-api 容器未运行${NC}"
    echo -e "${YELLOW}提示: 运行 'docker-compose up -d' 启动服务${NC}"
    exit 1
fi

if docker ps | grep -q "aether-db"; then
    echo -e "${GREEN}✅ aether-db 容器正在运行${NC}"
else
    echo -e "${RED}❌ aether-db 容器未运行${NC}"
    exit 1
fi
echo ""

# 等待服务就绪
echo "⏳ 等待服务启动（最多 60 秒）..."
timeout=60
elapsed=0
while [ $elapsed -lt $timeout ]; do
    if curl -sf http://localhost:8080/actuator/health > /dev/null 2>&1; then
        break
    fi
    sleep 2
    elapsed=$((elapsed + 2))
    echo -n "."
done
echo ""

if [ $elapsed -ge $timeout ]; then
    echo -e "${RED}❌ 服务启动超时${NC}"
    echo "查看日志: docker-compose logs aether-api"
    exit 1
fi
echo -e "${GREEN}✅ 服务已就绪${NC}"
echo ""

# 测试健康检查
echo "🏥 测试健康检查端点..."
health_response=$(curl -s http://localhost:8080/actuator/health)
if echo "$health_response" | grep -q "UP"; then
    echo -e "${GREEN}✅ 健康检查通过${NC}"
    echo "   响应: $health_response"
else
    echo -e "${RED}❌ 健康检查失败${NC}"
    echo "   响应: $health_response"
    exit 1
fi
echo ""

# 测试 Swagger UI
echo "📚 测试 API 文档..."
if curl -sf http://localhost:8080/swagger-ui.html > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Swagger UI 可访问${NC}"
    echo "   URL: http://localhost:8080/swagger-ui.html"
else
    echo -e "${YELLOW}⚠️  Swagger UI 暂时无法访问${NC}"
fi
echo ""

# 测试 OpenAPI 文档
echo "📄 测试 OpenAPI 文档..."
if curl -sf http://localhost:8080/v3/api-docs > /dev/null 2>&1; then
    echo -e "${GREEN}✅ OpenAPI 文档可访问${NC}"
    echo "   URL: http://localhost:8080/v3/api-docs"
else
    echo -e "${YELLOW}⚠️  OpenAPI 文档暂时无法访问${NC}"
fi
echo ""

# 测试 MySQL 连接
echo "🗄️  测试 MySQL 连接..."
if docker exec aether-db mysqladmin ping -h localhost -u root -paether_password > /dev/null 2>&1; then
    echo -e "${GREEN}✅ MySQL 连接正常${NC}"
else
    echo -e "${RED}❌ MySQL 连接失败${NC}"
    exit 1
fi
echo ""

# 显示容器资源使用情况
echo "📊 容器资源使用情况:"
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" aether-api aether-db
echo ""

# 最终总结
echo "========================================="
echo -e "${GREEN}✅ 部署验证完成！${NC}"
echo "========================================="
echo ""
echo "🎉 所有检查通过！aether 平台已成功部署。"
echo ""
echo "📖 快速链接:"
echo "   - API 文档:    http://localhost:8080/swagger-ui.html"
echo "   - OpenAPI:     http://localhost:8080/v3/api-docs"
echo "   - 健康检查:    http://localhost:8080/actuator/health"
echo ""
echo "💡 有用的命令:"
echo "   - 查看日志:    docker-compose logs -f"
echo "   - 重启服务:    docker-compose restart"
echo "   - 停止服务:    docker-compose down"
echo ""
