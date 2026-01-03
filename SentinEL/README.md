# 🛡️ SentinEL - 智能客户留存 AI 系统

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue?logo=python" alt="Python">
  <img src="https://img.shields.io/badge/Next.js-16-black?logo=next.js" alt="Next.js">
  <img src="https://img.shields.io/badge/Google%20Cloud-Vertex%20AI-4285F4?logo=google-cloud" alt="Google Cloud">
  <img src="https://img.shields.io/badge/LangChain-LangGraph-green" alt="LangChain">
  <img src="https://img.shields.io/badge/PyTorch-2.3+-EE4C2C?logo=pytorch" alt="PyTorch">
</p>

**SentinEL** (Sentinel + AI + EL) 是一个企业级 **AI 驱动的客户留存智能系统**，集成了机器学习流失预测、实时特征计算、LLM 智能代理和自动化 MLOps 管道，帮助企业识别高风险流失客户并制定个性化挽留策略。

---

## 📋 目录

- [核心功能](#-核心功能)
- [系统架构](#-系统架构)
- [技术栈](#-技术栈)
- [项目结构](#-项目结构)
- [快速开始](#-快速开始)
- [模块说明](#-模块说明)
- [API 文档](#-api-文档)
- [部署指南](#-部署指南)
- [开发指南](#-开发指南)

---

## ✨ 核心功能

### 🤖 智能 AI Agent
- **ReAct 决策框架**: 基于 LangGraph 构建的多步推理 Agent
- **工具调用能力**: 自动获取用户画像、预测流失风险、查询市场情报
- **个性化策略生成**: 结合用户价值和竞品动态制定挽留方案
- **邮件自动生成**: 为高价值用户生成个性化挽留邮件草稿
- **多模态竞品分析**: 解析竞品优惠截图，提取价格劣势情报

### 📊 机器学习引擎
- **LSTM 流失预测模型**: 基于用户行为序列的时序预测
- **Transformer 多模态模型**: 融合行为序列与用户特征的高级模型
- **推荐系统**: 双塔模型支持策略/商品个性化推荐
- **Vertex AI 集成**: 云端训练与模型端点部署

### ⚡ 实时数据管道
- **Apache Beam 流处理**: 实时点击流事件聚合
- **滑动窗口计算**: 毫秒级用户行为特征更新
- **Feature Store 集成**: 低延迟特征服务支持在线推理

### 🔄 MLOps 自动化
- **Kubeflow Pipelines**: 自动化模型训练与评估
- **A/B 测试框架**: 策略效果对比实验
- **模型版本管理**: 自动注册与灰度发布

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Frontend (Next.js 16)                         │
│                     React 19 + TailwindCSS + Recharts                   │
└─────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         Backend (FastAPI)                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │  Analysis   │  │    Agent    │  │   MLOps     │  │   Events    │    │
│  │     API     │  │ Orchestrator│  │     API     │  │     API     │    │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
          │                │                │                │
          ▼                ▼                ▼                ▼
┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│  BigQuery   │   │ Vertex AI   │   │   Pub/Sub   │   │  Firestore  │
│   (Data)    │   │   (ML/LLM)  │   │  (Events)   │   │   (State)   │
└─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘
                         │
                         ▼
          ┌─────────────────────────────┐
          │      ML Engine (PyTorch)    │
          │  LSTM / Transformer / RecSys│
          └─────────────────────────────┘
```

---

## 🛠️ 技术栈深度解析与选型思考

本项目并非技术的简单堆砌，而是针对"实时流失预测"这一复杂业务场景的精心架构。

### 🖥️ 前端架构: 极致的交互体验
> **挑战**: 传统的 AI Dashboard 往往数据枯燥、交互延迟高。
> **方案**: 采用 Next.js 16 + React 19 + Glassmorphism 打造沉浸式体验。

*   **Next.js 16 (App Router & Server Actions)**
    *   **深度应用**: 利用 **React Server Components (RSC)** 减少 40% 的客户端 JavaScript 体积；通过 **Server Actions** 处理表单提交，实现了无 API 胶水代码的开发模式，大幅提升开发效率和类型安全。
    *   **性能优化**: 实施了 Route Segment Config 进行增量静态再生成 (ISR)，确保静态页面的秒开体验。
*   **交互动效 (Framer Motion)**
    *   **深度应用**: 实现了基于物理引擎的布局动画 (Layout Animations) 和共享元素转换 (Shared Element Transitions)。
    *   **视觉语言**: 采用了 **Glassmorphism (毛玻璃)** 设计风格，通过多层 `backdrop-filter: blur()` 和半透明混合模式，营造出具有空间感和未来感的界面，符合 AI 产品的高端调性。
*   **数据可视化 (Recharts + Custom SVG)**
    *   **深度应用**: 高度定制化的雷达图和面积图，支持响应式布局和暗色模式自适应，直观展示高维特征数据。

### 🧠 后端核心: Agentic Workflow 与高并发
> **挑战**: 大模型推理耗时长，且需要处理非线性的复杂决策逻辑。
> **方案**: 基于 LangGraph 的异步编排与 ReAct 模式。

*   **LangGraph (Stateful Agent Orchestration)**
    *   **架构决策**: 放弃简单的 Chain 结构，选择 **LangGraph** 构建有环图（Cyclic Graph）。
    *   **实现细节**: Agent 拥有持久化的 State 状态机，能够在 "思考-行动-观察" 的循环中自我纠正错误。支持 **Human-in-the-loop** 模式，允许人工在关键步骤（如发送敏感邮件前）介入审批。
*   **FastAPI (Microservices)**
    *   **工程实践**: 充分利用 Python 的 `async/await` 协程处理 IO 密集型任务（如并发调用 Vertex AI 和 BigQuery），相比同步框架吞吐量提升 5-10 倍。
    *   **可观测性**: 集成 **OpenTelemetry** 进行分布式链路追踪，能够精确定位 Agent 在调用链中任一环节（如 Tool Execution）的延迟瓶颈。
*   **Redis (Semantic Caching)**
    *   **性能优化**: 不仅缓存简单的 Key-Value，还用于存储 Agent 的 "短期记忆" 和会话上下文，将重复的用户画像查询延迟从 200ms (BigQuery) 降低至 <5ms。

### 🔮 机器学习引擎: 深度学习与 MLOps 闭环
> **挑战**: 用户行为数据极其稀疏，且模型上线后易发生概念漂移 (Concept Drift)。
> **方案**: Transformer 时序模型 + 自动化 CT/CD 流水线。

*   **PyTorch (Advanced Architectures)**
    *   **模型设计**: 实现了基于 **Transformer Encoder** 的时序模型和 **LSTM** (长短期记忆网络)，能够有效捕捉长达 90 天的用户点击流序列中的隐性模式。
    *   **双塔推荐 (Two-Tower RecSys)**: 分别构建 User Tower 和 Item Tower，通过点积计算相似度，实现毫秒级的个性化策略召回。
*   **Google Vertex AI (End-to-End ML)**
    *   **Feature Store**: 构建了特征超市，确保训练数据（离线）和推理数据（在线）的一致性，彻底解决 "Training-Serving Skew" 难题。
    *   **Matching Engine**: 部署了高维向量索引服务，支持亿级向量的近似最近邻搜索 (ANN)，用于 "Look-alike" 人群扩散。
*   **Kubeflow Pipelines (MLOps)**
    *   **自动化**: 编排了 `Data Access -> Validation (TFDV) -> Training -> Eval -> Push` 的全链路。
    *   **持续训练**: 设置了基于性能阈值的自动触发器，一旦线上模型 AUC 下降，立即触发重训练流程。

### 🌊 数据工程: 实时流处理
> **挑战**: 只有在用户点击发生的瞬间进行干预，挽留成功率才最高。
> **方案**: Cloud Pub/Sub + Apache Beam 实时计算。

*   **Apache Beam (Streaming Analytics)**
    *   **技术细节**: 使用了 **Sliding Windows (滑动窗口)** 和 **Watermarks (水位线)** 机制，精确处理乱序到达的事件流，实现 "最近 1 小时点击次数" 等特征的秒级更新。
    *   **架构**: 采用 Lambda 架构，同时维护批处理（历史回溯）和流处理（实时干预）两条链路。

---

## 📁 项目结构深度剖析

---

## 📁 项目结构

```
SentinEL/
├── backend/                    # 后端微服务
│   ├── app/
│   │   ├── agents/            # AI Agent 实现
│   │   │   ├── sentinel_agent.py   # ReAct Agent (LangGraph)
│   │   │   └── tools.py            # Agent 工具定义
│   │   ├── api/v1/endpoints/  # REST API 端点
│   │   │   ├── analysis.py    # 用户分析 API
│   │   │   ├── agent.py       # Agent 编排 API
│   │   │   ├── mlops.py       # MLOps 管理 API
│   │   │   └── recommendations.py  # 推荐 API
│   │   ├── core/              # 核心配置
│   │   ├── models/            # 数据模型
│   │   └── services/          # 业务服务
│   ├── mlops/                 # MLOps 管道
│   │   ├── retraining_pipeline.py  # 自动重训练管道
│   │   └── components.py      # KFP 组件
│   └── Dockerfile
│
├── frontend/                   # Next.js 前端
│   ├── src/
│   │   ├── app/               # App Router 页面
│   │   │   ├── page.tsx       # 主页
│   │   │   └── dashboard/     # 仪表盘
│   │   ├── components/        # UI 组件
│   │   ├── hooks/             # 自定义 Hooks
│   │   └── services/          # API 服务层
│   └── package.json
│
├── ml_engine/                  # 机器学习引擎
│   ├── models/                # 模型定义
│   │   ├── churn_lstm.py      # LSTM 流失预测模型
│   │   └── churn_transformer.py  # Transformer 模型
│   ├── recsys/                # 推荐系统
│   ├── training/              # 训练脚本
│   ├── serving/               # 模型服务
│   ├── train_on_vertex.py     # Vertex AI 训练提交
│   └── deploy_endpoint.py     # 端点部署
│
├── data_engineering/           # 数据工程
│   └── streaming_pipeline.py  # Beam 流处理管道
│
├── simulation/                 # 流量模拟
│   ├── traffic_gen.py         # 流量生成器
│   └── live_traffic_gen.py    # 实时流量生成
│
├── scripts/                    # 运维脚本
│   ├── setup_pubsub.sh        # Pub/Sub 配置
│   └── setup_feature_store_resources.py
│
├── main.py                     # 简化版 Agent 入口
├── deploy_production.sh        # 一键云端部署脚本
├── requirements.txt            # Python 依赖
└── firebase.json               # Firebase 配置
```

---

## 🚀 快速开始

### 前置要求

- Python 3.11+
- Node.js 18+
- Google Cloud SDK
- Docker (可选)

### 1. 克隆项目

```bash
git clone https://github.com/wssAchilles/maccode.git SentinEL
cd SentinEL
```

### 2. 配置环境变量

```bash
# 创建 .env 文件
cat > .env << EOF
PROJECT_ID=your-gcp-project-id
LOCATION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
# 前端可选配置 (默认使用 localhost:8080)
NEXT_PUBLIC_API_URL=https://your-backend-url
NEXT_PUBLIC_API_KEY=your-api-key-if-needed
EOF
```

### 3. 启动后端

```bash
# 安装依赖
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 启动服务
uvicorn app.main:app --reload --port 8080
```

### 4. 启动前端

```bash
cd frontend
npm install
npm run dev
```

### 5. 访问应用

- 前端: http://localhost:3000
- 后端 API: http://localhost:8080
- API 文档: http://localhost:8080/docs

---

## 📦 模块说明

### AI Agent (`backend/app/agents/`)

基于 LangGraph 的 ReAct Agent，执行多步推理决策：

```python
# 工作流程
1. lookup_user_profile     # 获取用户画像
2. predict_churn_risk      # 预测流失风险
3. consult_market_intelligence  # 查询市场情报
4. find_retention_strategies    # 匹配挽留策略
5. check_budget_availability    # 预算检查
6. 生成个性化挽留邮件
```

### ML 模型 (`ml_engine/models/`)

```python
from ml_engine.models import create_model

# 创建 LSTM 模型
lstm_model = create_model(model_type="lstm", vocab_size=30)

# 创建 Transformer 模型
transformer_model = create_model(model_type="transformer", vocab_size=30)
```

### 流式管道 (`data_engineering/`)

```bash
# 启动 Dataflow 作业
python data_engineering/streaming_pipeline.py \
    --project $PROJECT_ID \
    --region us-central1 \
    --input_subscription projects/$PROJECT_ID/subscriptions/clickstream-sub \
    --runner DataflowRunner
```

---

## 📚 API 文档

### 用户分析

```http
POST /api/v1/analyze
Content-Type: application/json
X-API-Key: your-api-key

{
  "user_id": "63826"
}
```

**响应示例:**

```json
{
  "analysis_id": "uuid-xxx",
  "status": "PROCESSING"
}
```

### Agent 调用

```http
POST /api/v1/agent/invoke
Content-Type: application/json

{
  "user_id": "63826",
  "query": "分析该用户的流失风险并制定挽留策略"
}
```

### 健康检查

```http
GET /health

{
  "status": "healthy",
  "service": "SentinEL Backend",
  "version": "1.0.0"
}
```

---

## 🚢 部署指南

### 一键部署 (推荐)

项目包含自动化部署脚本，可一键将前后端部署到 Cloud Run 并处理 Redis 连接。

```bash
# 执行部署脚本
./deploy_production.sh
```

脚本将自动执行以下操作：
1. 检查本地环境工具 (gcloud, docker)
2. 构建并推送后端 Docker 镜像
3. 自动检测 Redis 实例并配置 VPC 连接
4. 部署后端服务到 Cloud Run
5. 获取后端 URL 并注入到前端构建参数
6. 构建并部署前端服务
7. 输出最终访问地址

### 手动部署 (作为参考)

如果需要单独更新服务：

```bash
# 后端部署
cd backend
gcloud run deploy sentinel-backend \
    --source . \
    --region us-central1 \
    --allow-unauthenticated

# 前端部署
cd frontend
gcloud run deploy sentinel-frontend \
    --source . \
    --region us-central1 \
    --set-env-vars NEXT_PUBLIC_API_URL=https://sentinel-backend-xxx.run.app
```

### Vertex AI 模型训练

```bash
python ml_engine/train_on_vertex.py \
    --project $PROJECT_ID \
    --region us-central1 \
    --data_path gs://your-bucket/training_data/sequences.csv \
    --staging_bucket gs://your-bucket
```

### MLOps 管道部署

```bash
# 编译管道
python backend/mlops/retraining_pipeline.py

# 提交到 Vertex AI Pipelines
gcloud ai pipelines submit \
    --project $PROJECT_ID \
    --region us-central1 \
    --pipeline-root gs://your-bucket/pipeline-root \
    sentinel_retraining_pipeline.json
```

---

## 👨‍💻 开发指南

### 代码风格

- Python: 遵循 PEP 8，使用 Black 格式化
- TypeScript: 遵循 ESLint 配置

### 运行测试

```bash
# 后端测试
cd backend
pytest

# 模型测试
python test_models.py
```

### 本地模拟

```bash
# 启动流量模拟器
python simulation/traffic_gen.py
```

---

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件。

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

<p align="center">
  Made with ❤️ by SentinEL Team
</p>
