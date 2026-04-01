# Cerberus v1

面向量化交易与高频撮合的工业级事件驱动微服务骨架。

## 架构

- 外部链路：`React -> Rust Gateway`，通过 REST + WebSocket 通信。
- 内部链路：服务契约定义在 `proto/` 下，使用 gRPC + Protobuf。
- 异步事件总线：Redis Streams（消费者组主链路）+ Redis Pub/Sub（旧版回退）。
- 服务：
  - `apps/frontend`：React + TypeScript + Zustand + Lightweight Charts + Firebase SDK 启动层。
  - `services/gateway-rs`：Rust Axum 网关，负责 Binance 行情流摄取、Redis 发布、REST/WS API。
    - 启动 / 引导骨架：
      - `bootstrap/config.rs`：环境加载与运行时策略校验。
      - `bootstrap/router.rs`：路由组合与 middleware / cors 装配。
      - `main.rs`：仅保留生命周期编排。
    - 订单摄取骨架：
      - `ingest/orders.rs`：摄取编排入口。
      - `ingest/orders/stream.rs`：Redis Stream 消费者组摄取 / reclaim / poison 路径。
      - `ingest/orders/stream/stream_group.rs`：消费者组初始化与 pending replay。
      - `ingest/orders/stream/{stream_io,stream_payload,stream_processing,stream_reclaim}.rs`：流读取 / 解析 / 处理 / reclaim 单元。
      - `ingest/orders/pubsub.rs`：旧版 Pub/Sub 回退。
      - `ingest/orders/stream_metrics.rs`：Stream 摄取指标状态迁移。
    - Strategy 上游骨架：
      - `handlers/trading/strategy/upstream.rs`：请求编排。
      - `handlers/trading/strategy/upstream/{error,queue,circuit,metrics}.rs`：上游运行时关注点。
  - `services/strategy-py`：FastAPI 量化服务 + Gurobi 均值方差优化接口。
    - 可选的 Firebase Firestore 信号持久化。
    - 运行时骨架：
      - `runtime_container.py`：依赖装配。
      - `signal_service.py` / `summary_service.py` / `matching_service/`：面向 API 的应用服务。
      - `system_status_service.py`：ready / metrics / persistence 应用服务。
      - `signal_engine_service.py`：按标的的信号引擎编排。
      - `worker_idempotency.py`：幂等所有权控制。
      - `worker_lifecycle.py`：worker 启停 / supervisor 生命周期。
      - `market_ingest_runtime/` 包：市场数据摄取编排：
        - `loop.py` / `pubsub_runtime.py` / `stream_runtime.py`
        - `stream_io.py` / `stream_processing.py` / `stream_reclaim.py`
        - `retry.py` / `time_utils.py`
      - `event_runtime/` 包：发布 / relay 编排：
        - `publish.py` / `matching_submission.py` / `relay.py`
        - `envelope.py` / `model.py`
  - `services/matching-cpp`：C++20 撮合核心 + 订单服务层（执行日志、快照 / 统计）+ GTest。
    - 当存在 `gRPC + Protobuf` 依赖时启用 gRPC 构建路径。
    - gRPC 运行时骨架：
      - `grpc_order_service_common.cpp`：启动、运行时参数与领域枚举 / 时间戳转换。
      - `grpc_order_service_context.cpp`：schema / correlation 传播与 degraded / backpressure 元数据。
      - `grpc_order_service_backpressure.cpp`：inflight permit 获取 / 释放与 timeout / retry 节奏控制。
      - `grpc_order_service_telemetry.cpp`：submit 延迟窗口 / P95 / 吞吐 / uptime 统计。
      - `grpc_order_service_{submit,order_lifecycle,orderbook,executions,health_stats}.cpp`：RPC 处理器。
- 基础设施：
  - 本地：Docker Compose（`redis`、`postgres`、`timescaledb`、全部应用服务）。
  - 云端：Firebase Hosting（前端）+ Cloud Run（gateway / strategy）+ Upstash Redis + Supabase Postgres，由 `infra/terraform` 下的 Terraform 统一创建。
  - Cloud Run 运行时容量配置由 Terraform 按服务管理（`cloud_run_gateway`、`cloud_run_strategy`、`cloud_run_matching`）。

## API（v1）

- Gateway 对外接口：
  - `GET /ready`
  - `GET /metrics`（Prometheus）
  - `GET /api/v1/klines`
  - `GET /api/v1/orderbook/snapshot?symbol=BTCUSDT`
  - `GET /api/v1/metrics`
  - `GET /api/v1/orders/events/recent`（支持 `limit`,`channel`,`account_id`,`symbol`,`order_id`,`status`,`request_id`）
  - `GET /api/v1/external/status`
  - `GET /api/v1/strategy/summary`
  - `GET /api/v1/trading/policy`
  - `GET /api/v1/binance/symbol-rules`
  - `POST /api/v1/binance/order/test`
  - `GET /api/v1/alpaca/account`
  - `POST /api/v1/alpaca/orders`
  - `POST /api/v1/alpaca/orders/{order_id}/cancel`
  - `WS /ws/market`
- `WS /ws/orders`
  - 从 Redis channel 推送结构化订单事件（默认：`strategy.signals.default`、`trade.executions.default`）
  - 同时推送 Gateway 自身生成的执行事件：Binance 测试下单 / Alpaca 提交 / Alpaca 撤单
  - 每条消息都包含 `channel`、`payload`、`received_at`
  - 执行事件 payload 使用统一字段：`event`、`provider`、`account_id`、`order_id`、`symbol`、`status`、`request_id`
- Strategy 接口：
  - `GET /ready`
  - `GET /metrics`（Prometheus）
  - `POST /api/v1/optimize/mean-variance`
  - `GET /api/v1/signal`
  - `GET /api/v1/signals/recent`
  - `GET /api/v1/status/persistence`
  - `GET /api/v1/summary`（供 Gateway 使用、带回退逻辑的内部聚合接口）
  - `POST /api/v1/signal/ingest`
  - `POST /api/v1/matching/orders`
  - `POST /api/v1/matching/orders/{order_id}/cancel`
  - `GET /api/v1/matching/orders/{order_id}`
  - `GET /api/v1/matching/executions`（支持 `account_id`，可选 `symbol`,`order_id`,`request_id`）
  - `GET /api/v1/matching/health`
  - `GET /api/v1/matching/stats`
  - `GET /api/v1/matching/orderbook?symbol=BTCUSDT&depth=10`

请求追踪与错误模型：

- Gateway 和 Strategy 都支持 `x-request-id` 传播（并在响应头中回显）。
- Gateway 在变更类 API 上支持 `idempotency-key` / `x-idempotency-key`，并回显规范化后的值。
- Gateway 上游探测接口（`/api/v1/external/status`）会把 `x-request-id` 继续转发给 Strategy 健康检查。
- Gateway REST 返回统一包络：`{ "request_id", "data", "error" }`，成功时 `error` 为 `null`。
- 核心执行 API 在成功 payload 中也会包含 `request_id`，方便前端追踪完整流程。

本地契约冒烟：

- `./scripts/smoke_local.sh` 会校验 `/health`、`/ready`、`/metrics`、`x-request-id` 传播，以及统一错误包络。

前端运行时环境变量：

- `VITE_GATEWAY_BASE`
- `VITE_STRATEGY_BASE`
- `VITE_AUTH_REQUIRED`
- `VITE_FIREBASE_API_KEY`
- `VITE_FIREBASE_AUTH_DOMAIN`
- `VITE_FIREBASE_PROJECT_ID`
- `VITE_FIREBASE_STORAGE_BUCKET`
- `VITE_FIREBASE_MESSAGING_SENDER_ID`
- `VITE_FIREBASE_APP_ID`
- `VITE_DISABLE_LIVE_STREAM`（测试 / e2e 需要确定性时设为 `true`）

Firebase Authentication 行为：

- 登录页只提供邮箱登录和 Google 登录。
- 没有独立的“公共首页”，当前前端在启用鉴权时会先进入登录闸门，再进入工作台。
- 生产环境下，只要 Firebase Web SDK 配置存在，就默认启用登录闸门；不再要求显式设置 `VITE_AUTH_REQUIRED=true`。
- 如需在某个环境下强制关闭登录闸门，可显式设置 `VITE_AUTH_REQUIRED=false`。
- 如需在本地或预览环境下强制开启登录闸门，可显式设置 `VITE_AUTH_REQUIRED=true`。
- 邮箱登录使用 Firebase Email/Password，输入已存在账号时直接登录。
- 邮箱创建账号使用单独的“创建账号”动作，不再走“登录失败后自动注册”的隐式回退。
- Google 登录使用 Firebase onboarding，首次登录也会自动创建账号。

生产前端最小鉴权配置：

- `VITE_FIREBASE_API_KEY`
- `VITE_FIREBASE_AUTH_DOMAIN`
- `VITE_FIREBASE_PROJECT_ID`
- `VITE_FIREBASE_STORAGE_BUCKET`
- `VITE_FIREBASE_MESSAGING_SENDER_ID`
- `VITE_FIREBASE_APP_ID`

只要上述配置完整，生产 bundle 就会默认进入登录面板；如果配置缺失，登录面板会显示“登录服务尚未完成配置”。

## 快速开始

1. 将 Python 依赖同步到已有 `.venv`：

```bash
source .venv/bin/activate
uv lock --project services/strategy-py
uv sync --project services/strategy-py --python .venv/bin/python --active --frozen --all-groups
```

运行 Strategy 测试：

```bash
source .venv/bin/activate
uv run --project services/strategy-py --active pytest services/strategy-py/tests
```

2. 安装前端依赖：

```bash
cd apps/frontend && npm install && cd ../..
```

前端质量门禁：

```bash
cd apps/frontend
npm run test
npm run build
npm run check:bundle-budget
npm run test:e2e
npm run lighthouse
```

已部署版本门禁（针对线上地址）：

```bash
cd apps/frontend
E2E_BASE_URL="https://<your-hosting-url>" E2E_GATE_MODE=true E2E_USE_DEPLOYED=true E2E_AUTH_EMAIL="gate-user@example.com" E2E_AUTH_PASSWORD="replace_me" npm run test:e2e:gate
LHCI_COLLECT_URL="https://<your-hosting-url>" npm run lighthouse:gate
```

`npm run lighthouse:gate` 会同时执行桌面端和移动端 SLO 断言。  
注意：Lighthouse 的导航型运行不一定总能产出 INP（`auditRan=0`），因此门禁中把 INP 视为 warning；真正的响应性硬门禁使用 `total-blocking-time`。

3. 启动本地栈：

```bash
docker compose up -d --build
```

Prometheus（本地 Compose）地址：

- [http://localhost:9090](http://localhost:9090)

4. 打开前端：

- [http://localhost:5173](http://localhost:5173)

5. 初始化 GCP 项目 API：

```bash
./scripts/bootstrap_gcp.sh cerberus-9d94f asia-east2
```

6. 运行非容器化冒烟测试：

```bash
make smoke
```

7. 初始化 Supabase 信号表（可选）：

```bash
export SUPABASE_DB_URL=postgresql://...
uv run --with "psycopg[binary]" scripts/bootstrap_supabase_signals.py
```

8. 同步交易所密钥并从源码部署 gateway：

```bash
export BINANCE_API_KEY=...
export BINANCE_API_SECRET=...
export ALPACA_API_KEY=...
export ALPACA_API_SECRET=...
./scripts/sync_gcp_exchange_secrets.sh cerberus-9d94f asia-east2
./scripts/deploy_gateway_source.sh cerberus-9d94f asia-east2
./scripts/deploy_strategy_source.sh cerberus-9d94f asia-east2
```

如果需要更快地重复发布 gateway，可使用缓存镜像部署：

```bash
./scripts/deploy_gateway_cached.sh cerberus-9d94f asia-east2
```

统一部署脚本骨架：

- `scripts/deploy_common.sh` 是 Gateway / Strategy / Matching 三条 Cloud Run 发布脚本的共享底座。
- 共享能力包括：
  - `Artifact Registry` 预检
  - `Cloud Build` 显式构建
  - `Cloud Run` 镜像部署
  - 临时 YAML 自动清理
  - `DRY_RUN`
  - `GCLOUD_QUIET`
- 当前推荐发布顺序：
  1. `./scripts/deploy_gateway_source.sh <project> <region>`
  2. `./scripts/deploy_strategy_source.sh <project> <region>`
  3. `./scripts/deploy_matching_source.sh <project> <region>`
  4. `cd apps/frontend && npm run build && firebase deploy --only hosting --project <project>`
- 如需先看完整命令展开而不真正执行，可设置：

```bash
DRY_RUN=true ./scripts/deploy_gateway_source.sh cerberus-9d94f asia-east2
```

## Colab 训练与 ONNX 导出复盘

这一节记录了 Cerberus 在 Colab 上训练时序信号模型、导出 ONNX，并接入线上推理链路时踩过的关键坑。重点不是“某次调参用了什么数值”，而是把真正影响稳定性的工程认知固定下来，避免后续再次重复犯错。

### 调整过程中的认知变化

训练脚本的调整过程大致经历了五个阶段：

1. 第一阶段：优先“榨干 H100”
   - 最初的关注点是把 `batch_size`、`d_model`、`transformer_layers`、`ff_dim`、`lstm_hidden` 等参数尽可能拉高，希望最大化利用 H100 的 80GB 显存和 Hopper 架构。
   - 这一阶段的直觉是“显卡越强，模型越大越好”，但后面发现，对时序模型来说，算力并不是唯一瓶颈，样本组织方式和导出链路的稳定性往往更重要。

2. 第二阶段：优先“修正类别不平衡”
   - 在看到 `HOLD` 远多于 `BUY/SELL` 之后，最先尝试的是强行做标签平衡，包括严格下采样和随机重采样。
   - 后来确认，这类方法对图像或普通表格数据可能可行，但对需要连续时间窗口的 LSTM / Transformer 是高风险操作。

3. 第三阶段：优先“保护训练成果”
   - 训练跑到一半被 Colab 中断、浏览器断开或主动停止，都会直接损失最好的一轮模型。
   - 因此训练产物的管理从“最后统一保存一次”改成了“每个 epoch 都留 checkpoint，并把最终冠军模型单独归档到 `best_model` 目录”。

4. 第四阶段：优先“让 ONNX 真正导出来”
   - 训练能跑通不代表产物能进入生产。导出 ONNX 的过程中，PyTorch 2.x 的新导出器、Transformer 快速路径、LSTM 与 FakeTensor / Dynamo 的兼容性问题陆续暴露出来。
   - 这一阶段的认知转变是：导出成功依赖的是“兼容性优先”的图生成策略，而不是把训练态和导出态完全复用。

5. 第五阶段：优先“保证验证对象是干净模型”
   - 在为导出 ONNX 修改 `dropout`、切换 `train()`、改写 forward 路径后，直接拿内存中的模型做 sanity check 容易得到误导性结果。
   - 最后沉淀出的规则是：任何导出后的验证，都必须基于“重新实例化并重新加载权重”的干净模型，不能直接相信刚被导出逻辑修改过的内存对象。

### 典型错误、根因与修复方式

#### 1. H100 仍然 OOM，不是因为数据行数，而是单步图太大

现象：

- 即使缩小了总训练行数，只要把 `batch_size` 拉得过高，仍会在训练阶段触发显存不足。

原因：

- 对时序模型，显存占用与“单步计算图大小”强相关，而不只是与总样本数相关。
- 当 `lookback=256`、Transformer 层数较多、隐藏维度较大时，自注意力的开销会随着 `batch_size` 和序列长度迅速膨胀。
- 因此从 `1024` 直接提升到 `4096` 这类做法，即使 H100 也可能撑不住。

修复：

- 不再用“显卡大就无脑翻倍 batch”的方式调参。
- 回退到稳定的 `batch_size`，优先保证训练可持续跑完，再逐步扩模型。
- 结论：H100 的价值不仅是更大 batch，也包括更快收敛和更高吞吐，但前提是计算图本身必须可控。

#### 2. 训练断掉就丢最好模型，根因是只在最后一次性保存

现象：

- 训练到中途断开，最佳 epoch 的参数直接丢失，只剩日志。

原因：

- 原始脚本把 `best_state` 的写盘动作放在整个 `for epoch in range(...)` 结束之后。
- 这意味着只要 Colab 断连、手动停止、内核重启，哪怕前面已经出现最佳指标，也不会留下稳定产物。

修复：

- 每个 epoch 都写入一次 `epoch_checkpoints/`。
- 训练结束后再把冠军模型单独复制到 `best_model/`。
- 现在 Cerberus 的训练产物规范默认要求保留：
  - 每轮 checkpoint（用于恢复和排查）
  - 单独的 `best_model` 目录（用于接入线上系统）

#### 3. 用随机采样做标签平衡，破坏了时序连续性

现象：

- 模型训练虽然能跑，但输出开始退化成几乎恒定的决策或固定置信度。
- 指标表面上可能还能看，但线上意义很差。

原因：

- LSTM / Transformer 依赖连续的时间窗口。
- 一旦对时序表做 `sample(frac=1.0)`、严格随机下采样，或者任何打乱行顺序的标签平衡操作，就会把本来连续的 `lookback` 窗口切成随机碎片。
- 这种输入不再代表真实市场序列，模型学到的也不是有效时序模式。

修复：

- 不再对训练样本做随机洗牌式平衡。
- 如果必须缩减数据量，使用“按标的保留最近一段连续历史”的方式，例如按 symbol 截取最新若干行，再按时间排序。
- 当前的稳定原则是：
  - 保留时序连续性优先于追求标签绝对均衡
  - 优先使用损失函数权重处理不平衡，而不是随机打乱样本序列

#### 4. Host RAM 被打爆，不是模型太大，而是裁剪顺序错了

现象：

- 不是 GPU OOM，而是 Colab 主机 RAM 被打满，运行时直接重启。

原因：

- 过早对全量原始数据做 `lazy.collect()` 和滚动特征计算，会让 Polars 在极大数据集上生成庞大的中间结果。
- 如果“先全量特征工程，再裁剪到最近一段历史”，那么内存峰值已经在裁剪前发生了。

修复：

- 先按 symbol 截断数据，再做特征工程。
- 原则是“先瘦身，再化妆”：
  - 先把每个标的裁到最近一段连续历史
  - 再进入 rolling / feature engineering / collect
- 这样不仅更省 RAM，也能明显减少预处理时间。

#### 5. 类别权重过猛，导致模型几乎把所有样本都判成少数类

现象：

- 训练开始后准确率和宏平均 F1 很差，模型明显过度倾向 `BUY/SELL` 这类少数类。

原因：

- 直接使用极端的逆频率权重会把少数类损失放大得过头。
- 在 `HOLD` 极多、`BUY/SELL` 极少的情况下，模型会为了避免少数类损失，被迫把大量样本预测成少数类。

修复：

- 不使用生硬的 `1.0 / count` 级别权重。
- 改用更平滑的权重，例如平方根平滑后的逆频率。
- 这样仍然能照顾少数类，但不会把决策边界直接拉崩。

#### 6. `checkpoint` 变量污染命名空间，导致训练函数本身报错

现象：

- 后续训练阶段突然出现 `TypeError: 'dict' object is not callable` 这类看起来和模型本身无关的错误。

原因：

- 在调试单元里写了 `checkpoint = torch.load(...)`，覆盖了原本从 `torch.utils.checkpoint` 导入的 `checkpoint()` 函数。
- 后面训练代码再次调用 `checkpoint(...)` 时，拿到的是字典而不是函数。

修复：

- 调试和验证单元里不使用 `checkpoint` 作为变量名，改用 `ckpt` 等名字。
- 更重要的是，把所有调试 / 推理 / 导出试验单元放到训练主流程之后，避免污染训练上下文。
- 一旦发生过覆盖，最安全的恢复手段是直接重启 Colab runtime。

#### 7. ONNX 导出失败，根因是 PyTorch 2.x 新导出器和融合快速路径不稳定

现象：

- 导出阶段先后遇到：
  - 缺少 `onnxscript`
  - FakeTensor / data pointer 相关报错
  - `aten::_transformer_encoder_layer_fwd` 不支持

原因：

- 新版 ONNX 导出路径依赖额外包，并且在包含 LSTM、Transformer、CUDNN、FakeTensor 的复杂组合下，兼容性并不稳定。
- 当模型进入 `eval()` 后，PyTorch 可能会切到 fused Transformer encoder fast path；这个路径中的部分底层算子并没有稳定的 ONNX 映射。

修复：

- 导出不追求“最新导出器”，而追求“最稳导出器”。
- 最后收敛出的稳定策略是：
  - 使用旧导出路径：`dynamo=False`
  - 关闭 fused attention 快速路径
  - 用兼容性优先的导出上下文生成图
  - 在必要时以 `training` 图模式导出，绕过 `eval` 态 fused operator
- 这也是为什么最终导出时看到一些 warning 仍可接受：这些 warning 是为了换取可部署产物，而不是训练本身出错。

#### 8. 导出后直接做 sanity check，得到“伪正确”或恒定输出

现象：

- 导出成功后，立刻用内存中的模型跑测试，出现近似恒定概率、固定置信度或明显异常的预测。

原因：

- 为了导出成功，往往会临时修改模型对象：
  - 替换 `dropout`
  - 切换 `train()`
  - 调整 forward 路径
- 这些操作会污染当前内存中的模型状态。
- 如果此时直接把这个对象拿去做验证，就不是在验证“原始训练模型”，而是在验证“被导出逻辑改写过的模型对象”。

修复：

- 导出后任何 sanity check 都必须重新实例化一个干净模型，再加载 checkpoint。
- 如果怀疑 `best_model/cerberus_signal_model.pt` 也在错误时机被污染，就回退到对应的 `epoch_checkpoints/model_epoch_<best>.pt` 重建冠军模型。
- 训练、导出、验证三步必须显式隔离，而不是混在同一个内存对象生命周期里。

### 最终沉淀出的稳定训练策略

综合上面的错误链，当前推荐的稳定流程如下：

1. 数据裁剪阶段
   - 先按 symbol 保留最近一段连续历史。
   - 不对时序样本做随机乱序或随机重采样。
   - 在进入 rolling / feature engineering 之前就完成裁剪。

2. 不平衡处理阶段
   - 优先使用平滑 class weight。
   - 不用随机平衡去破坏时间顺序。

3. 训练阶段
   - 模型规模和 `batch_size` 逐步增大，不以“显卡够大”为唯一依据。
   - 每个 epoch 都保存 checkpoint。
   - `best_model` 单独归档。

4. 导出阶段
   - ONNX 导出优先兼容性，不强行使用最新导出路径。
   - 避免 fused Transformer 快速路径导致的导出失败。
   - 导出脚本和训练脚本可以共存，但导出逻辑不得污染训练完成后的“验证对象”。

5. 验证阶段
   - 始终基于“重新实例化 + 重新加载权重”的干净模型做验证。
   - 不直接拿刚被导出逻辑改写过的内存模型做结论。

### 当前 Cerberus 推荐的模型产物规范

Colab 训练仍然全部发生在云端，但进入 Cerberus 线上推理链时，产物必须满足当前项目的 artifact 规范。最小产物集如下：

- `artifact_manifest.json`
- `training_metrics.json`
- `preprocessing.json`
- `cerberus_signal_model.onnx`
- `cerberus_signal_model.pt`（仅兼容旧产物时需要；有 `preprocessing.json` 时可以不作为生产运行时依赖）

规范详情见：

- [ARTIFACT_SPEC.md](/Users/achilles/Documents/code/Cerberus/research/ARTIFACT_SPEC.md)

当前线上运行时的推荐方式是：

- 训练：Colab 云端
- 产物归档：GCS `best_model` 前缀
- 线上加载：Strategy 启动时从 GCS 拉取 `manifest + metrics + preprocessing + onnx`
- 线上推理：Cloud Run 内使用 ONNX Runtime

当前运行时会优先读取 `preprocessing.json`，只有旧产物缺少该文件时，才会回退读取 `cerberus_signal_model.pt`，相关实现见：

- [inference_artifacts.py](/Users/achilles/Documents/code/Cerberus/services/strategy-py/app/infrastructure/inference_artifacts.py)

推荐的 GCS 前缀结构如下：

```text
gs://<bucket>/models/cerberus-transformer-lstm/v1/best_model/
  artifact_manifest.json
  training_metrics.json
  preprocessing.json
  cerberus_signal_model.onnx
  cerberus_signal_model.pt
```

这样做的原因有两个：

- 训练继续完全发生在 Colab 云端，不占本机算力。
- 生产环境不需要依赖 Google Drive 网页下载路径，也不需要在 Cloud Run 里保留 `torch` 作为常驻推理依赖。

## Gurobi 与 Firebase 密钥

- 不要把密钥提交进版本控制。
- 本地运行变量请以 `deploy/compose/.env.example` 为模板。
- GCP 部署请使用 Secret Manager，并映射为运行时环境变量。

重要：如果任何 Gurobi WLS 凭证曾在聊天记录或截图中暴露，请立刻到 Gurobi 控制台轮换，并同步更新 Secret Manager。

## 云端密钥映射（GCP）

- `cerberus-dev-upstash-redis-url` -> `REDIS_URL`（`rediss://...`，必须启用 TLS）
- `cerberus-dev-upstash-redis-rest-url` -> `UPSTASH_REDIS_REST_URL`
- `cerberus-dev-upstash-redis-rest-token` -> `UPSTASH_REDIS_REST_TOKEN`
- `cerberus-dev-supabase-project-url` -> `SUPABASE_PROJECT_URL`
- `cerberus-dev-supabase-anon-key` -> `SUPABASE_ANON_KEY`
- `cerberus-dev-supabase-service-role-key` -> `SUPABASE_SERVICE_ROLE_KEY`
- `cerberus-dev-supabase-db-url` -> `SUPABASE_DB_URL`
- `cerberus-dev-gurobi-licenseid` -> `GRB_LICENSEID`
- `cerberus-dev-gurobi-wlsaccessid` -> `GRB_WLSACCESSID`
- `cerberus-dev-gurobi-wlssecret` -> `GRB_WLSSECRET`
- `cerberus-dev-firebase-web-api-key` -> `FIREBASE_WEB_API_KEY`
- `cerberus-dev-jwt-hs256-secret` -> `JWT_HS256_SECRET`
- `cerberus-dev-binance-api-key` -> `BINANCE_API_KEY`
- `cerberus-dev-binance-api-secret` -> `BINANCE_API_SECRET`
- `cerberus-dev-alpaca-api-key` -> `ALPACA_API_KEY`
- `cerberus-dev-alpaca-api-secret` -> `ALPACA_API_SECRET`

Gateway Stream 环境变量：

- `REDIS_ORDERBOOK_CHANNEL`（市场扇出 channel）
- `REDIS_ORDERBOOK_CHANNEL_PREFIX`（按 symbol 分发的市场 channel 前缀，默认 `md.orderbook`）
- `REDIS_TICK_CHANNEL_PREFIX`（按 symbol 分发的 tick channel 前缀，默认 `md.ticks`）
- `REDIS_MARKET_EVENTS_STREAM_ENABLED` / `REDIS_MARKET_EVENTS_STREAM_KEY` / `REDIS_MARKET_EVENTS_STREAM_MAXLEN`
- `REDIS_MARKET_EVENTS_PUBLISH_LEGACY_PUBSUB`（仅 stream，或与旧版 pubsub 双写）
- `MARKET_SYMBOLS`（逗号分隔的 Binance 标的，例如 `BTCUSDT,ETHUSDT`）
- `MARKET_WS_URL`（可选的显式市场 WS 地址；Binance Futures 可用 `wss://fstream.binance.com/stream?streams=btcusdt@bookTicker/ethusdt@bookTicker`）
- `KLINE_API_URL`（可选的显式 K 线接口地址；Binance Futures 测试链路可用 `https://demo-fapi.binance.com/fapi/v1/klines`）
- `REDIS_ORDER_EVENTS_CHANNELS`（`/ws/orders` 订阅的订单事件 channel，逗号分隔）
- `REDIS_ORDER_EVENTS_STREAM_ENABLED` / `REDIS_ORDER_EVENTS_STREAM_KEY` / `REDIS_ORDER_EVENTS_CONSUMER_GROUP` / `REDIS_ORDER_EVENTS_CONSUMER_NAME`
- `REDIS_ORDER_EVENTS_LEGACY_PUBSUB_FALLBACK`（stream 摄取失败时是否允许降级到旧版 Pub/Sub；若要强制 stream-first，请设为 `false`）
- 生产运行时策略：`REDIS_ORDER_EVENTS_LEGACY_PUBSUB_FALLBACK=false`、`REDIS_MARKET_EVENTS_PUBLISH_LEGACY_PUBSUB=false`，以及 strategy 侧 `EVENT_STREAM_PUBLISH_LEGACY_PUBSUB=false`
- `REDIS_ORDER_EVENTS_READ_BATCH_SIZE` / `REDIS_ORDER_EVENTS_READ_BLOCK_MS` / `REDIS_ORDER_EVENTS_PENDING_REPLAY_COUNT` / `REDIS_ORDER_EVENTS_BATCH_WINDOW_MS`
- `REDIS_ORDER_EVENTS_MAX_RETRIES_BEFORE_FALLBACK` / `REDIS_ORDER_EVENTS_RETRY_BACKOFF_MS` / `REDIS_ORDER_EVENTS_RETRY_BACKOFF_MAX_MS`
- `REDIS_ORDER_EVENTS_RECLAIM_ENABLED` / `REDIS_ORDER_EVENTS_RECLAIM_INTERVAL_MS` / `REDIS_ORDER_EVENTS_RECLAIM_IDLE_MS` / `REDIS_ORDER_EVENTS_RECLAIM_BATCH_SIZE`
- `REDIS_ORDER_EVENTS_MAX_DELIVERY_ATTEMPTS` / `REDIS_ORDER_EVENTS_POISON_STREAM_KEY` / `REDIS_ORDER_EVENTS_POISON_STREAM_MAXLEN`
- `REDIS_ORDER_EVENTS_PENDING_WARN_THRESHOLD` / `REDIS_ORDER_EVENTS_LAG_WARN_THRESHOLD`
- `STRATEGY_SUMMARY_CACHE_TTL_MS`（Gateway 侧 `/api/v1/strategy/summary` 的短期缓存）
- `STRATEGY_SUMMARY_BATCH_WINDOW_MS`（Gateway 在拉取上游 summary 前的 single-flight 合并窗口）
- `READY_MAX_MARKET_STALENESS_MS`（可选 ready 门禁；设为 `0` 则关闭市场新鲜度检查）
- `UNIT_REQUEST_COST_USD`（Gateway `/metrics` 与 `/api/v1/metrics` 使用的单请求成本基线）
- `JWT_AUTH_ENABLED` / `JWT_AUTH_REQUIRE_IN_PRODUCTION` / `JWT_HS256_SECRET` / `JWT_ISSUER` / `JWT_AUDIENCE`
- `BINANCE_API_KEY` / `BINANCE_API_SECRET`（签名 Binance REST）
- `BINANCE_ORDER_TEST_PATH`（默认 `/api/v3/order/test`；Futures API 可用 `/fapi/v1/order/test`）
- `ALPACA_API_KEY` / `ALPACA_API_SECRET` / `ALPACA_TRADING_BASE_URL`
- `STRATEGY_BASE_URL`（Gateway `/api/v1/external/status` 用于探测上游 strategy 的可选地址）
- `STRATEGY_INTERNAL_AUTH_ENABLED` / `STRATEGY_INTERNAL_AUTH_AUDIENCE` / `STRATEGY_INTERNAL_AUTH_TOKEN_TTL_SECONDS`
- `GCP_METADATA_IDENTITY_URL`（需要时可覆盖 metadata identity endpoint）
- `STRATEGY_UPSTREAM_TIMEOUT_MS` / `STRATEGY_UPSTREAM_HEALTH_TIMEOUT_MS`
- `STRATEGY_UPSTREAM_MAX_INFLIGHT` / `STRATEGY_UPSTREAM_QUEUE_TIMEOUT_MS`
- `STRATEGY_UPSTREAM_CIRCUIT_ENABLED` / `STRATEGY_UPSTREAM_CIRCUIT_FAILURE_THRESHOLD` / `STRATEGY_UPSTREAM_CIRCUIT_OPEN_MS`
- `TRADING_POLICY_ENFORCED`（服务端风险门禁）
- `BINANCE_ALLOWED_SYMBOLS` / `ALPACA_ALLOWED_SYMBOLS`
- `MAX_BINANCE_ORDER_QTY` / `MAX_BINANCE_ORDER_NOTIONAL_USD`
- `MAX_ALPACA_ORDER_QTY` / `MAX_ALPACA_LIMIT_NOTIONAL_USD`
- `MATCHING_SUBMIT_LATENCY_WINDOW_SIZE`（撮合 submit P95 的滚动样本窗口）
- `MATCHING_MAX_INFLIGHT_REQUESTS` / `MATCHING_INFLIGHT_ACQUIRE_TIMEOUT_MS`（撮合 backpressure 预算 / 排队等待）
- `MATCHING_BACKPRESSURE_RETRY_SLEEP_MS`（等待 inflight 预算时的重试 sleep）
- `MATCHING_GRPC_MAX_POLLERS` / `MATCHING_GRPC_MIN_POLLERS` / `MATCHING_GRPC_NUM_CQS`

Gateway 对外交易接口：

- `POST /api/v1/binance/order/test`（签名测试接口，不会下真实订单）
- `GET /api/v1/alpaca/account`
- `POST /api/v1/alpaca/orders`

信号持久化路径：

- Ingest（Gateway / 手动）-> Strategy -> Firestore + Supabase `strategy_signals`
- Matching 执行 relay（Strategy）-> Redis `trade.executions.<account_id>` -> Gateway `/ws/orders`
- Strategy 会把统一流事件发到 `EVENT_STREAM_KEY`，包络如下：
  - `event_type`、`event_id`、`created_at`、`schema_version`、`payload`（可选 `correlation_id`）
  - 发布控制项：`EVENT_STREAM_ENABLED`、`EVENT_STREAM_KEY`、`EVENT_STREAM_MAXLEN`、`EVENT_STREAM_PUBLISH_LEGACY_PUBSUB`
- Strategy 幂等可以使用基于 Redis 的 claim：
  - `IDEMPOTENCY_STORE_REDIS_ENABLED`、`IDEMPOTENCY_REDIS_KEY_PREFIX`、`SIGNAL_IDEMPOTENCY_TTL_SECONDS`
- Strategy 市场数据摄取可使用 Redis Stream 消费者组：
  - `MARKET_STREAM_ENABLED`、`MARKET_STREAM_KEY`、`MARKET_STREAM_CONSUMER_GROUP`、`MARKET_STREAM_LEGACY_PUBSUB_FALLBACK`
  - `MARKET_STREAM_RECLAIM_ENABLED`、`MARKET_STREAM_RECLAIM_INTERVAL_MS`、`MARKET_STREAM_RECLAIM_IDLE_MS`、`MARKET_STREAM_RECLAIM_BATCH_SIZE`
  - `MARKET_STREAM_MAX_DELIVERY_ATTEMPTS`、`MARKET_STREAM_POISON_STREAM_KEY`、`MARKET_STREAM_POISON_STREAM_MAXLEN`
  - `MARKET_STREAM_PENDING_WARN_THRESHOLD`、`MARKET_STREAM_LAG_WARN_THRESHOLD`
- Matching gRPC schema 回退可通过以下变量固定：
  - `CERBERUS_EVENT_SCHEMA_VERSION`（默认 `v1`）

Matching 服务运行时能力：

- 价格优先、时间优先撮合核心
- 订单生命周期跟踪（`NEW/PARTIALLY_FILLED/FILLED/CANCELED/REJECTED`）
- 带按账户查询辅助的执行日志
- 当构建启用 gRPC 依赖时，提供 `OrderService`（submit / cancel / get / stream）
- 提供 gRPC health / stats 可观测接口（`Health`、`GetServiceStats`）
- Matching 的 degraded 信号是显式的：
  - `Health.status=degraded:*`
  - gRPC trailing metadata `x-cerberus-degraded` / `x-cerberus-degraded-reason`
  - 强制 degraded 模式下，业务 RPC 会以 `UNAVAILABLE` 失败，不会静默返回空 stream / 空 orderbook
- Matching `GetServiceStats` 现在包含容量基线：
  - `submit_order_requests_total`、`submit_order_errors_total`、`submit_order_rejections_total`
  - `submit_order_latency_p95_ms`、`submit_order_throughput_rps`、`trade_throughput_rps`
  - `inflight_requests`、`inflight_requests_peak`、`max_inflight_requests`
  - `backpressure_waits_total`、`backpressure_rejections_total`、`backpressure_wait_timeouts_total`、`backpressure_wait_ms_total`
  - 运行时参数回显：`execution_stream_limit`、`submit_latency_window_size`、`grpc_min_pollers`、`grpc_max_pollers`、`grpc_num_cqs`
- 默认禁用非 gRPC fallback 二进制启动（`MATCHING_ALLOW_STUB_STARTUP=true` 可启用仅诊断用途的 warmup）
- 本地 gRPC 构建命令：`cmake -S services/matching-cpp -B services/matching-cpp/build-grpc -DENABLE_GRPC_SERVICE=ON`

OrderService RPC 列表：

- `SubmitOrder`
- `CancelOrder`
- `GetOrder`
- `GetOrderBook`
- `StreamExecutions`
- `Health`
- `GetServiceStats`

Proto 工作流：

- 源契约位于 `proto/cerberus/*/v1`
- 运行 `buf lint && buf generate` 生成：
  - Python：`services/strategy-py/app/gen`
  - C++：`services/matching-cpp/gen`
  - Rust：`services/gateway-rs/src/gen`
  - TS：`apps/frontend/src/gen`

## GCP 项目默认值

- Project：`cerberus-9d94f`
- Region：`asia-east2`
- Environment：仅 `dev`

## CI/CD

GitHub Actions 工作流 `.github/workflows/ci.yml` 会执行：

- Terraform 基础设施检查（`fmt`、`init -backend=false`、`validate`）
- Python 测试（strategy）
- Rust `cargo check`（gateway）
- C++ 构建与测试（matching）
- 前端单测 + Playwright e2e + build + Lighthouse 断言
- 可选的 Buf 检查（当 runner 上可用 `buf` 时）

云端部署工作流为 `.github/workflows/deploy.yml`：

- 构建并部署 `gateway-rs` 与 `strategy-py` 到 Cloud Run。
- 构建前端并部署到 Firebase Hosting。
- 对 Firebase Hosting 做安全头 / 缓存策略校验（`scripts/validate_frontend_hosting.sh`）。
- 针对线上 Firebase URL 执行已部署 e2e / lighthouse gate。
- 针对已部署 gateway 运行后端 deploy gate，校验延迟 / 吞吐 / 单位成本阈值（`scripts/gateway_perf_gate.py`）。
- 认证门禁依赖 GitHub Secrets：`FIREBASE_E2E_EMAIL` 与 `FIREBASE_E2E_PASSWORD`。
- 交易接口依赖交易所密钥：`BINANCE_API_KEY`、`BINANCE_API_SECRET`、`ALPACA_API_KEY`、`ALPACA_API_SECRET`。
- 还依赖 `JWT_HS256_SECRET`，并会执行 `scripts/validate_deploy_policy.sh` 作为 deploy gate。

运维参考：

- `docs/ops/runbook-stream-reliability.md`
- `docs/ops/alerts-and-slo.md`
- `docs/ops/capacity-baseline.md`

## 部署后 Chrome DevTools MCP 门禁（手动发布阻断项）

使用已部署的 Firebase Hosting URL 作为唯一验收入口：

1. 在桌面视口打开线上站点并验证：
   - 市场卡片会刷新
   - Binance 测试下单的 precheck -> submit -> response 正常闭环
   - Alpaca submit + cancel 路径能闭环
   - matching 订单簿面板与执行时间线保持联动
2. 再在移动端视口重复一次（验证可用性，不要求与桌面同等信息密度）。
3. 检查控制台：
   - 任何 `error` 级别日志都视为阻断发布
4. 检查网络：
   - 核心 API（`/api/v1/strategy/summary`、`/api/v1/klines`、`/api/v1/binance/symbol-rules`、`/api/v1/trading/policy`、`/api/v1/binance/order/test`、`/api/v1/alpaca/orders`）不得返回 `4xx/5xx`
5. 性能 SLO：
   - LCP <= 2.0s
   - INP <= 150ms（通过交互 trace / field probe 测量）
   - CLS < 0.1

## 前端云端发布入口

推荐使用仓库根目录脚本统一构建、发布并执行前端云端门禁：

```bash
E2E_AUTH_EMAIL="gate-user@example.com" \
E2E_AUTH_PASSWORD="replace_me" \
./scripts/deploy_frontend_hosting.sh
```

脚本会完成：

- 解析 Firebase Web SDK 配置
- 以 Cloud Run gateway 为上游构建前端
- 发布到 Firebase Hosting live channel
- 校验 Hosting 安全头、缓存策略与产物中不存在本地地址
- 针对已部署 URL 执行 Lighthouse gate
- 当提供 `E2E_AUTH_EMAIL` / `E2E_AUTH_PASSWORD` 时，再执行 deployed e2e gate

鉴权态验收补充：

1. 必须使用真实 Firebase 账号完成一次表单登录，不再依赖开发期的临时 bearer 注入。
2. 登录成功后，页头应出现：
   - 当前登录邮箱
   - “退出登录”按钮
3. 登录后的网络请求必须满足：
   - `POST https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword` 返回 `200`
   - `GET /api/v1/strategy/summary` 返回 `200`
   - `GET /api/v1/klines` 返回 `200`
   - `GET /api/v1/trading/policy` 返回 `200`
   - `GET /api/v1/binance/symbol-rules` 返回 `200`
   - `GET /api/v1/orders/events/recent` 返回 `200`
4. 登录后的 `Overview / Market / Execution` 至少要验证：
   - `Overview`：推理可观测、策略编排、组合级信号摘要
   - `Market`：分钟 K 线、策略决策篮子、组合级信号摘要、订单簿摘要
   - `Execution`：执行生命周期、交易工单、策略决策篮子、执行回报时间线
5. 如果匿名访问时 `strategy summary` 返回 `401`，这属于预期降级路径；但一旦完成登录，继续出现 `401` 就视为阻断发布。
