# 🐳 Docker 容器化部署指南

本文档详细说明如何使用 Docker 部署数据科学全栈应用（Flask 后端 + Flutter Web 前端）。

---

## 📋 目录

- [系统要求](#系统要求)
- [项目架构](#项目架构)
- [快速开始](#快速开始)
- [详细配置](#详细配置)
- [构建镜像](#构建镜像)
- [运行容器](#运行容器)
- [生产部署](#生产部署)
- [常见问题](#常见问题)

---

## 系统要求

- **Docker**: >= 20.10
- **Docker Compose**: >= 2.0
- **内存**: >= 4GB (构建 Flutter Web 需要较多内存)
- **磁盘空间**: >= 10GB

### 检查 Docker 版本

```bash
docker --version
docker compose version
```

---

## 项目架构

```
├── back/                      # Flask 后端
│   ├── Dockerfile            # 后端 Docker 镜像定义
│   ├── .dockerignore         # 后端构建忽略文件
│   ├── .env.example          # 环境变量示例
│   └── ...
├── front/                     # Flutter 前端源码
│   └── lib/
├── Dockerfile.frontend        # 前端 Docker 镜像定义 (多阶段构建)
├── docker-compose.yml         # 服务编排配置
├── nginx.conf                 # Nginx 配置 (SPA 路由支持)
├── .dockerignore              # 根目录构建忽略文件
└── README_DOCKER.md           # 本文档
```

### 服务说明

| 服务 | 端口 | 描述 |
|------|------|------|
| `backend` | 8080 | Flask API + Gurobi 优化器 + Firebase |
| `frontend` | 3000 | Flutter Web (Nginx 托管) |

---

## 快速开始

### 1️⃣ 配置环境变量

```bash
# 复制环境变量模板
cp back/.env.example back/.env

# 编辑并填入你的凭证
nano back/.env  # 或使用你喜欢的编辑器
```

### 2️⃣ 启动服务

```bash
# 构建并启动所有服务
docker compose up --build

# 或者后台运行
docker compose up --build -d
```

### 3️⃣ 访问应用

- **前端**: <http://localhost:3000>
- **后端 API**: <http://localhost:8080/api/health>

---

## 详细配置

### 环境变量说明

在 `back/.env` 文件中配置以下必要变量：

#### GCP / Firebase 配置

```env
GCP_PROJECT_ID=your-project-id
STORAGE_BUCKET_NAME=your-bucket.appspot.com

# 服务账号凭证 (两种方式选一)
# 方式1: 挂载凭证文件
GOOGLE_APPLICATION_CREDENTIALS=/app/credentials/service-account-key.json

# 方式2: 使用 Workload Identity (GKE/Cloud Run)
# 无需设置，自动获取
```

#### Gurobi WLS 许可证

```env
GRB_LICENSEID=2743684
GRB_WLSACCESSID=your-access-id
GRB_WLSSECRET=your-secret
```

> ⚠️ **安全提示**: 永远不要将 `.env` 文件提交到 Git！

### GCP 服务账号配置

如果需要访问 Firebase/GCS，你需要：

1. 创建服务账号并下载 JSON 密钥
2. 在 `docker-compose.yml` 中添加卷挂载：

```yaml
services:
  backend:
    volumes:
      - ./credentials:/app/credentials:ro
```

3. 将密钥文件放入 `credentials/service-account-key.json`

---

## 构建镜像

### 单独构建后端

```bash
cd back
docker build -t datascience-backend:latest .
```

### 单独构建前端

```bash
docker build -f Dockerfile.frontend -t datascience-frontend:latest .
```

### 使用 Docker Compose 构建

```bash
# 构建所有服务
docker compose build

# 强制重新构建（不使用缓存）
docker compose build --no-cache
```

---

## 运行容器

### 开发环境

```bash
# 启动所有服务（前台运行，查看日志）
docker compose up

# 只启动后端
docker compose up backend

# 只启动前端
docker compose up frontend
```

### 生产环境

```bash
# 后台运行
docker compose up -d

# 查看运行状态
docker compose ps

# 查看日志
docker compose logs -f

# 只查看后端日志
docker compose logs -f backend
```

### 停止服务

```bash
# 停止所有服务
docker compose down

# 停止并删除数据卷
docker compose down -v
```

---

## 生产部署

### 部署到 Google Cloud Run

```bash
# 1. 构建并推送后端镜像
cd back
gcloud builds submit --tag gcr.io/YOUR_PROJECT/datascience-backend

# 2. 部署到 Cloud Run
gcloud run deploy datascience-backend \
  --image gcr.io/YOUR_PROJECT/datascience-backend \
  --platform managed \
  --region asia-northeast1 \
  --allow-unauthenticated \
  --set-env-vars "GRB_LICENSEID=xxx,GRB_WLSACCESSID=xxx,GRB_WLSSECRET=xxx"
```

### 部署到 Kubernetes (GKE)

```bash
# 1. 创建 Secret
kubectl create secret generic backend-secrets \
  --from-env-file=back/.env

# 2. 应用部署配置
kubectl apply -f k8s/
```

### 资源配置建议

| 环境 | CPU | 内存 | 说明 |
|------|-----|------|------|
| 开发 | 1 | 1GB | 本地测试 |
| 生产 | 2 | 2GB | Gurobi 需要较多资源 |
| 高负载 | 4 | 4GB | 大规模优化任务 |

---

## 常见问题

### Q1: 构建 Flutter 镜像很慢？

Flutter 首次构建需要下载 SDK 和依赖，可能需要 10-15 分钟。后续构建会使用缓存。

**优化建议**：

- 使用 BuildKit 加速：`DOCKER_BUILDKIT=1 docker compose build`
- 确保网络畅通

### Q2: Gurobi 许可证错误？

确保 WLS 环境变量正确设置：

```bash
# 检查容器内环境变量
docker compose exec backend env | grep GRB
```

### Q3: Firebase 连接失败？

检查服务账号配置：

```bash
# 确保凭证文件存在
docker compose exec backend ls -la /app/credentials/

# 检查环境变量
docker compose exec backend env | grep GOOGLE
```

### Q4: 端口被占用？

修改 `docker-compose.yml` 中的端口映射：

```yaml
ports:
  - "8081:8080"  # 改为其他端口
```

### Q5: 如何查看容器内部？

```bash
# 进入后端容器
docker compose exec backend /bin/bash

# 进入前端容器 (Alpine 使用 sh)
docker compose exec frontend /bin/sh
```

---

## 健康检查

### 后端健康检查

```bash
curl http://localhost:8080/api/health
```

### 前端健康检查

```bash
curl http://localhost:3000/health
```

---

## 镜像大小

| 镜像 | 大小 | 说明 |
|------|------|------|
| backend | ~800MB | 包含 Python + 数据科学库 |
| frontend | ~25MB | Nginx Alpine + 静态文件 |

---

## 🔗 相关文档

- [Docker 官方文档](https://docs.docker.com/)
- [Docker Compose 参考](https://docs.docker.com/compose/)
- [Google Cloud Run 文档](https://cloud.google.com/run/docs)
- [Gurobi WLS 配置](https://www.gurobi.com/documentation/current/remoteservices/licensing.html)

---

## 📝 更新日志

- **2025-11-25**: 初始版本，支持 Flask 后端 + Flutter Web 前端容器化
