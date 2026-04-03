# 🚀 服务部署指南 (Deployment Guide)

此文档包含了针对 **混合双核架构 (Hybrid Dual-Core)** 的部署指令。请根据您修改的代码部分选择对应的部署命令。

## 1. 部署 App Engine (Light Core)
**适用场景**: 修改了通用 API、文件上传、历史记录等轻量级功能。
**配置文件**: `back/app.yaml`

```bash
cd "/Users/achilles/Documents/code/data science/back"

# 部署到 App Engine 标准环境
gcloud app deploy app.yaml
```

---

## 2. 部署 Cloud Run (Heavy Core)
**适用场景**: 修改了 Deep Learning、RAG (知识库)、TensorFlow 相关代码或 `backend/services/` 下的重型服务。
**配置文件**: `back/Dockerfile`

### 方法 A: 使用我们可以提供的自动脚本 (推荐)
我们在 `scripts/` 目录下准备了优化过的部署脚本：

```bash
cd "/Users/achilles/Documents/code/data science"

# 赋予执行权限 (仅需一次)
chmod +x scripts/deploy_cloud_run.sh

# 运行部署
./scripts/deploy_cloud_run.sh
```

### 方法 B: 手动命令行部署
如果您想手动控制每一步：

```bash
cd "/Users/achilles/Documents/code/data science/back"

# 1. 构建镜像并提交到 Google Container Registry (GCR)
gcloud builds submit --tag gcr.io/top-operand-445801-f0/sentinel-backend-cloudrun

# 2. 部署到 Cloud Run (显式指定大内存和 CPU)
gcloud run deploy sentinel-backend-cloudrun \
  --image gcr.io/top-operand-445801-f0/sentinel-backend-cloudrun \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 4Gi \
  --cpu 2
```

## 3. 部署前端 (Flutter Web)
**适用场景**: 修改了 `front/lib` 下的任何 UI 代码。

```bash
cd "/Users/achilles/Documents/code/data science/front"

# 1. 编译 Web 版本
flutter build web --release

# 2. 部署到 Firebase Hosting
firebase deploy --only hosting
```

---

## 4. 部署 Rust 控制面 (Sentinel Orchestrator)
**适用场景**: 修改了 `sentinel-orchestrator/` 或 Python 控制面调度边界，例如审批、取消、重试、Cloud Tasks 分发。

### 方法 A: 使用独立部署脚本

```bash
cd "/Users/achilles/Documents/code/data science"

chmod +x scripts/deploy_orchestrator.sh
./scripts/deploy_orchestrator.sh
```

### 方法 B: 手动部署到 Cloud Run

```bash
cd "/Users/achilles/Documents/code/data science/sentinel-orchestrator"

gcloud builds submit --tag gcr.io/<PROJECT_ID>/sentinel-orchestrator

gcloud run deploy sentinel-orchestrator \
  --image gcr.io/<PROJECT_ID>/sentinel-orchestrator \
  --platform managed \
  --region asia-northeast1 \
  --allow-unauthenticated \
  --set-env-vars PYTHON_WORKER_BASE_URL=https://<PROJECT_ID>.an.r.appspot.com,INTERNAL_JOB_TOKEN=<TOKEN>
```

### 接线说明

- App Engine / Python worker 继续保留现有 `INTERNAL_BASE_URL`
- 当 Rust sidecar 上线后，将 `ORCHESTRATOR_BASE_URL` 指向该 Cloud Run 服务
- 之后 Cloud Tasks 会优先把 `/internal/operations/{id}/dispatch` 投递给 Rust 控制面
