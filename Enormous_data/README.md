# 基于 Spark + Flask 的电商行为大数据分析看板

本项目按可扩展的大数据分析产品原型建设，同时可直接作为大数据课程设计交付。数据字段对齐 Kaggle `eCommerce behavior data from multi category store` 数据集。系统流程为：

```text
数据集 CSV/JSON/TXT/HDFS
  -> PySpark 读取、清洗、去重、聚合
  -> data/cache/*.json 指标缓存
  -> Flask API
  -> React + ECharts 独立前端
```

## 数据集

推荐使用 Kaggle 电商行为数据集，字段包括：

```text
event_time,event_type,product_id,category_id,category_code,brand,price,user_id,user_session
```

开发阶段可先生成同字段样例数据：

```bash
python scripts/generate_sample_data.py --rows 10000 --output data/sample/ecommerce_events.csv
```

真实数据下载后放入 `data/raw/`，再修改 `configs/local.yaml` 的 `data.input_path`。

真实 Kaggle 文件建议放在：

```text
data/raw/kaggle/ecommerce_behavior/
```

然后运行：

```bash
.venv/bin/python -m spark_jobs.main --config configs/kaggle.yaml
```

`configs/kaggle.yaml` 默认限制 `limit: 100000`，适合课程设计演示。需要全量处理时把 `limit` 留空。

## 本地运行

建议使用 Python 3.8。当前依赖固定在 `requirements.txt`。

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/generate_sample_data.py --rows 10000
.venv/bin/python -m spark_jobs.main --config configs/local.yaml
.venv/bin/flask --app run:app run --host 0.0.0.0 --port 5051
```

另开终端启动 React 前端：

```bash
cd frontend
npm install
npm run dev
```

访问：

```text
http://127.0.0.1:5173/
```

`frontend/vite.config.ts` 已将 `/api` 代理到 Flask 后端 `http://127.0.0.1:5051`。前端默认 API base 是 `/api/v1`，也可以通过 `VITE_API_BASE_URL` 覆盖。旧 Jinja 页面仍可访问，但主前端已经迁移为 `frontend/` 下的 React 应用。

## Docker

Dockerfile 固定使用 Python 3.11 和 OpenJDK，便于课设环境复现。本地 Docker 演示栈使用 `local-lab` profile，避免和 YARN 实验栈混启动。

```bash
docker compose --profile local-lab run --rm spark-job
docker compose --profile local-lab up web frontend
```

如果镜像源拉取失败，先检查 Docker Desktop 的镜像源配置，或改用本地虚拟环境运行。

## HDFS 可选模式

项目提供两个 HDFS 相关配置：

```text
configs/hdfs.yaml   # 强制读取 hdfs:///user/course/ecommerce_behavior/*.csv
configs/auto.yaml   # 课程演示用自动降级模板
```

无 Hadoop 环境时推荐继续使用本地模式。HDFS 只作为 raw/processed 的可选存储，Flask 仍读取本地 `data/cache/*.json`。

## Docker YARN 实验模式

`yarn-lab` profile 用于课程论文实验：HDFS + YARN + Spark on YARN client mode。它不会引入 Spark Standalone，资源由 YARN ResourceManager/NodeManager 管理。

Hadoop 容器固定使用 ARM64 本地构建镜像 `enormous-data-hadoop-arm64:slim-hadoop`。不要使用 `bde2020/*`、`linux/amd64` 镜像，也不要把 `docker commit master` 作为最终方案。当前 `docker/hadoop-arm64/Dockerfile` 依赖本地 `hadoop/` 与 `java-8-openjdk-arm64/` 构建输入，并从 `spark-client` 构建阶段复制裁剪后的 Python 3.11 运行时，保证 PySpark driver 与 executor 的 Python 小版本一致；如果 Hadoop/JDK 目录不存在，应使用可审计的 ARM64 构建或下载流程生成，不能从 amd64 容器或 master commit 产物复制。

```bash
docker compose --profile yarn-lab up -d yarn-namenode yarn-datanode-1 yarn-datanode-2 secondarynamenode resourcemanager nodemanager-1 nodemanager-2 spark-client spark-history-server
docker compose --profile yarn-lab exec spark-client /app/scripts/init_yarn_lab.sh
```

默认宿主机端口已避开 `master` 容器常用端口；容器内服务名和 YARN 配置不变。不要在 `master` 运行时把 YARN 实验栈改回宿主机 `9870/8088`，否则会发生端口冲突。需要自定义端口时，只改宿主机侧端口变量：

```bash
YARN_HDFS_UI_PORT=19870 YARN_RM_UI_PORT=18088 SPARK_HISTORY_UI_PORT=28080 docker compose --profile yarn-lab up -d yarn-namenode yarn-datanode-1 yarn-datanode-2 secondarynamenode resourcemanager nodemanager-1 nodemanager-2 spark-client spark-history-server
```

可选上传本地样本 CSV：

```bash
docker compose --profile yarn-lab exec spark-client /app/scripts/init_yarn_lab.sh /app/data/sample/ecommerce_events.csv
```

真实数据建议先生成用户级样本，再上传到 HDFS 做 1%/5% 梯度实验：

```bash
PERCENTS="1 5" ./scripts/prepare_yarn_samples.sh
```

将 CSV 放入 HDFS 后提交 Spark 作业：

```bash
docker compose --profile yarn-lab exec spark-client /app/scripts/submit_yarn_client.sh /app/configs/yarn-client.yaml yarn-demo-1pct
```

YARN/History UI：

```text
HDFS NameNode:        http://127.0.0.1:19870
YARN ResourceManager: http://127.0.0.1:18088
Spark History:        http://127.0.0.1:28080
```

`configs/yarn-client.yaml` 默认读取：

```text
hdfs:///user/course/ecommerce_behavior_user_sample_1pct/*.csv
```

第一阶段使用 YARN client mode，输出仍写到本地 `data/cache/*.json`，方便 Flask/React 继续读取。大结果和 processed 数据写入 HDFS Parquet，避免把全量明细拉回 driver。

Forecasting 模块只把 `top_entities + site` 的有界历史带入 driver 侧基线模型；`history_collect_days` 控制时间窗口，`max_driver_history_rows` 是硬上限，实际行数会写入 `forecasting_quality.metrics.driver_history_rows` 和 `forecasting_summary.max_driver_history_rows`。

实验 benchmark 示例：

```bash
.venv/bin/python scripts/benchmark.py --config configs/yarn-client.yaml --engines spark --profile pipeline --history-url http://127.0.0.1:28080
```

模块级 benchmark 采用 1% 样本中的 200,000 行典型数据，不跑全量 Oct+Nov：

```bash
for profile in affinity recommendation anomaly experimentation; do
  PYSPARK_PYTHON="$PWD/.venv/bin/python" \
  PYSPARK_DRIVER_PYTHON="$PWD/.venv/bin/python" \
  .venv/bin/python scripts/benchmark.py \
    --config configs/typical-module-benchmark.yaml \
    --engines spark \
    --profile "$profile" \
    --output-dir "data/benchmarks/module-typical-20260610/$profile"
done
```

完整对比矩阵建议在 `spark-client` 容器内运行，避免宿主机 Hadoop/YARN 环境差异：

```bash
docker compose --profile yarn-lab exec spark-client python /app/scripts/run_yarn_experiment_matrix.py --sample-label 1pct
docker compose --profile yarn-lab exec spark-client python /app/scripts/run_yarn_experiment_matrix.py --sample-label 5pct
```

矩阵会生成 `baseline_local_csv`、`yarn_only_csv`、`yarn_aqe_csv`、`yarn_algorithm_csv`、`yarn_parquet` 五组配置和结果。`yarn_parquet` 读取前一组优化 YARN 作业写出的 HDFS Parquet `events` 目录，用于对比 CSV 扫描与列式输入。

作业成功后，可从 Spark History Server 采集 shuffle、spill、失败 task 和 executor 内存指标：

```bash
.venv/bin/python scripts/collect_spark_history_metrics.py --history-url http://127.0.0.1:28080 --app-id <application_id> --output-dir data/benchmarks/yarn-smoke
```

当前 Spark 3.5.5 History Server 在解析超长 event log 字符串时可能触发 Jackson `StreamReadConstraints` 的 20,000,000 字符默认上限，表现为应用列表可见但 `/stages` API 返回 500。`configs/yarn-client.yaml` 已将 `spark.sql.maxPlanStringLength` 限制为 `8192`，用于降低后续实验 event log 过大的风险；已经生成的旧 event log 不会被 retroactive 修复。

如果 History Server API 仍返回 500，使用 event log 解析脚本绕过 UI API，直接从 HDFS rolling event log 中补采集指标：

```bash
.venv/bin/python scripts/backfill_benchmark_history_metrics.py --force
```

该命令会在正式 YARN benchmark 目录下写入 `spark_history_metrics.json/csv`，并生成 `data/benchmarks/spark-history-eventlog-backfill.json` 汇总文件。前端 Ops 页和质量页会优先读取这些 event log 指标。

采集脚本默认只读取 application、stages、executors API，不读取 `/jobs` API。对较大的 event log，`/jobs` 端点可能在 History Server 侧膨胀成很大的 JVM 对象并触发 Java heap OOM；论文实验需要的 shuffle、spill、失败/重试 task 和 executor 内存指标来自 stages/executors，默认路径更稳。如果确认 event log 很小且需要 job 级计数，可额外加 `--include-jobs`。

`scripts/benchmark.py` 在提供 `--history-url` 时会等待 Spark History Server 索引完成后，把 shuffle/spill/task 指标写入 benchmark row；如果课程机较慢，仍可用上面的 `collect_spark_history_metrics.py` 对同一个 `application_id` 补采集，形成独立 `spark_history_metrics.json/csv` 证据。

`web-yarn` 默认设置 `SPARK_HISTORY_URL=http://spark-history-server:18080`。通过 Flask `/api/v1/refresh` 触发的 YARN 作业会在 manifest 生成后 best-effort 采集 History 指标，并把 `spark_application_id`、`spark_application_status`、`spark_history_metrics_status` 和 `spark_history_metrics` 写入 Job API；采集失败只标记 `unavailable`，不会覆盖已成功的 Spark 作业状态。

`spark-history-server` 默认设置 `SPARK_DAEMON_MEMORY=${SPARK_HISTORY_DAEMON_MEMORY:-3g}`，并启用 History disk store、较小 application retention 和单线程 replay，避免在本机 Docker 环境一次性把多个大 UI 状态压进 JVM heap。`yarn-client.yaml` 默认使用 `spark.sql.ui.explainMode: simple`、event log 压缩/rolling 和 UI retention，避免大 SQL plan 或过多 UI 状态写入 event log 后导致 History API 解析失败。

YARN cluster mode 已提供第二阶段入口：

```bash
docker compose --profile yarn-lab exec spark-client /app/scripts/submit_yarn_cluster.sh /app/configs/yarn-cluster.yaml cluster-smoke
```

当前 Flask refresh 默认仍使用 client mode，因为 Flask/React 读取本地 `data/cache`。cluster mode 会把 driver 交给 NodeManager，后续若设为默认路径，需要把 JSON cache 改为 HDFS 输出读取或同步回 Flask 可读目录。

## API

所有 API 返回统一结构：

```json
{
  "code": 0,
  "message": "ok",
  "data": {},
  "meta": {}
}
```

核心接口：

```text
GET  /healthz
GET  /readyz
GET  /api/v1/health
GET  /api/v1/contracts
GET  /api/v1/openapi.json
GET  /api/v1/summary
GET  /api/v1/events/distribution
GET  /api/v1/trend/daily-events
GET  /api/v1/trend/daily-sales
GET  /api/v1/ranking/categories
GET  /api/v1/ranking/brands
GET  /api/v1/table?page=1&size=20&event_type=purchase
GET  /api/v1/job
POST /api/v1/refresh
```

普通 GET 接口只读取缓存，不实时执行 Spark。`POST /api/v1/refresh` 会启动后台 Spark 刷新任务。旧 `/api/*` 暂时保留兼容，并返回 `Deprecation: true` 响应头。

`GET /api/v1/contracts` 返回当前 API 端点、统一响应 envelope、错误码和核心数据模型。`GET /api/v1/openapi.json` 返回 OpenAPI 3.1 结构，可作为后续生成 TypeScript 类型、做契约 diff 和 CI 门禁的单一事实源。

## React 前端

前端为标准前后端分离架构：

```text
frontend/src/
  api/                 React Query hooks 与 query keys
  app/                 QueryClient 等应用级配置
  components/          通用组件、布局、反馈组件
  features/            业务特性组件
  pages/               路由页面
  routes/              React Router 配置
  lib/                 API client、格式化、图表 option
  styles/              视觉系统
```

核心前端依赖：

```text
React 19
Vite 7
React Router
TanStack Query
ECharts
anime.js
lucide-react
```

设计方向参考 anime.js 的分层动效理念：用 stagger/grid 动效强化信息入场和刷新反馈，不做干扰读数的高频动画。ECharts 已按需注册基础图表组件，Vite 已做手动分包。

前端验证：

```bash
cd frontend
npm run typecheck
npm run test
npm run build
npm run e2e:install
npm run e2e
```

Playwright 浏览器通过 `PLAYWRIGHT_BROWSERS_PATH=0` 安装到 `frontend/node_modules/playwright-core/.local-browsers`，不会写入全局 npm 包。`npm run test` 使用 Vitest + Testing Library + MSW，`npm run e2e` 使用 Playwright 并在测试内 mock `/api/v1/*`，因此 smoke 测试不依赖 Flask 服务正在运行。

## 验证

```bash
.venv/bin/python -m py_compile run.py app/*.py app/routes/*.py app/services/*.py spark_jobs/*.py scripts/generate_sample_data.py
.venv/bin/python -m pytest tests -q
.venv/bin/python -m spark_jobs.main --config configs/local.yaml
cd frontend && npm run typecheck
cd frontend && npm run test
cd frontend && npm run build
cd frontend && npm run e2e
```

性能对比：

```bash
.venv/bin/python scripts/benchmark.py --config configs/local.yaml --profile tiny
```

结果会写入：

```text
data/benchmarks/benchmark_results.json
data/benchmarks/benchmark_results.csv
```

实验报告素材见 [docs/report_materials.md](docs/report_materials.md)。

已验证：

- Spark 样例数据清洗与指标输出。
- Flask API 成功和参数错误路径。
- React 前端生产构建通过。
- React 前端通过 Vite proxy 访问 Flask API。
