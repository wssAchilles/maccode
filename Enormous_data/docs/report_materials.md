# 实验报告素材清单

## 截图清单

1. Kaggle 数据集页面截图。
2. `data/raw/kaggle/ecommerce_behavior/` 原始数据目录截图。
3. `python -m spark_jobs.main --config configs/kaggle.yaml` 运行成功终端截图。
4. `data/cache/*.json` 指标缓存目录截图。
5. Flask 首页 `/overview` 数据卡片截图。
6. ECharts 行为类型占比、每日事件趋势、类目排行截图。
7. `/table` 分页表格截图。
8. `scripts/benchmark.py` 性能对比运行截图。
9. `data/benchmarks/benchmark_results.csv` 表格截图。
10. 可选：`hdfs dfs -ls /user/course/ecommerce_behavior` 截图。
11. YARN ResourceManager `http://127.0.0.1:18088` 应用成功截图。
12. Spark History Server `http://127.0.0.1:28080` 事件日志截图。
13. HDFS `/spark-history` 与 processed Parquet 目录截图。
14. `data/benchmarks/benchmark_results.csv` 中 YARN 对比实验截图。

## 数据字段说明表

| 字段名 | 类型 | 含义 | 用途 |
| --- | --- | --- | --- |
| event_time | timestamp | 用户行为发生时间 | 趋势分析 |
| event_type | string | view/cart/remove_from_cart/purchase | 行为分布、转化分析 |
| product_id | long | 商品 ID | 商品排行 |
| category_id | long | 类目 ID | 类目聚合 |
| category_code | string | 类目层级文本 | 类目排行 |
| brand | string | 品牌 | 品牌排行 |
| price | double | 商品价格 | 销售额统计 |
| user_id | long | 用户 ID | 用户数统计 |
| user_session | string | 会话 ID | 会话数统计 |

## 数据规模设计

| profile | 行数 | 用途 |
| --- | ---: | --- |
| tiny | 10,000 | 功能验证、截图 |
| small | 100,000 | Spark/Pandas 基准对比 |
| medium | 1,000,000 | 展示 Spark 大数据处理优势 |
| user_sample_1pct | 用户级 1% 样本 | YARN 稳定性基线 |
| user_sample_5pct | 用户级 5% 样本 | YARN 压力测试 |
| oct_nov_full | Oct+Nov 全量 | 最终可行性实验；若本机资源不足则记录资源边界 |
| full | 全量 | 可选扩展 |

## 性能对比表模板

| 数据规模 | 任务 | Pandas 耗时 | Spark 耗时 | 结论 |
| --- | --- | ---: | ---: | --- |
| tiny | event_type_count | 待填 | 待填 | 小数据 Pandas 启动成本低 |
| small | daily_events | 待填 | 待填 | Spark 可稳定处理更大数据 |
| medium | top_categories | 待填 | 待填 | Spark 分区聚合优势更明显 |

## YARN 与内存优化实验矩阵

| 实验组 | 运行方式 | 优化点 | 观测指标 |
| --- | --- | --- | --- |
| baseline | local Spark + CSV | 原始 JSON 输出 | elapsed、driver 内存、是否 OOM |
| yarn_only | YARN client + CSV | 只切资源管理器 | YARN application status、container 日志 |
| yarn_aqe | YARN client + CSV | AQE、skew join、shuffle partitions | shuffle read/write、spill、task retries |
| yarn_algorithm | YARN client + CSV | preview collect、pair 限流、推荐质量 Spark 聚合 | recommendation preview 行数、pair_base_rows |
| yarn_parquet | YARN client + Parquet | 清洗后按 dt 分区 Parquet | rows/sec、扫描耗时、输出文件数 |

YARN 指标采集命令：

```bash
.venv/bin/python scripts/collect_spark_history_metrics.py --history-url http://127.0.0.1:28080 --app-id <application_id> --output-dir data/benchmarks/yarn-smoke
```

## 论文依据摘要

| 论文/系统 | 会议/来源 | 可落地思想 |
| --- | --- | --- |
| MapReduce | OSDI 2004 | 批处理抽象、容错、分区处理基线 |
| RDD/Spark | NSDI 2012 | lineage、内存计算、缓存复用 |
| Hadoop YARN | SoCC 2013 | ResourceManager/NodeManager/ApplicationMaster 资源模型 |
| Spark SQL/Catalyst | SIGMOD 2015 | DataFrame 优化器、列裁剪、谓词下推 |
| SkewTune | SIGMOD 2012 | 数据倾斜检测与长尾 task 风险 |
| Starfish | CIDR 2011 | profile-driven tuning，先测量后调参 |
| Themis | SoCC 2012 | 合理 spill/落盘，不追求全内存 |
| Spark CACM | CACM 2016 | 统一批处理、SQL、ML、图计算 |

## 系统流程

```text
Kaggle 原始数据
  -> 本地 data/raw 或 HDFS
  -> PySpark 读取
  -> 清洗：缺失值、异常价格、去重、时间转换
  -> 聚合：行为分布、每日趋势、销售额、类目排行、品牌排行
  -> data/cache JSON
  -> Flask API
  -> ECharts 看板和分页表格
```

## 验收命令

```bash
.venv/bin/python scripts/generate_sample_data.py --rows 10000
.venv/bin/python -m spark_jobs.main --config configs/local.yaml
.venv/bin/python scripts/benchmark.py --config configs/local.yaml --profile tiny
docker compose --profile yarn-lab up -d yarn-namenode yarn-datanode-1 yarn-datanode-2 secondarynamenode resourcemanager nodemanager-1 nodemanager-2 spark-client spark-history-server
docker compose --profile yarn-lab exec spark-client /app/scripts/init_yarn_lab.sh /app/data/sample/ecommerce_events.csv
docker compose --profile yarn-lab exec spark-client /app/scripts/submit_yarn_client.sh /app/configs/yarn-client.yaml yarn-demo-1pct
.venv/bin/python -m pytest tests -q
.venv/bin/flask --app run:app run --host 0.0.0.0 --port 5050
```
