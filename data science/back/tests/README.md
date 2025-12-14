# 后端测试指南

本项目包含多层次的测试脚本，用于验证 ML 服务、优化算法和 API 接口。

## 目录结构 (`back/tests/`)

* **`test_api_integration.py`**: Web API 集成测试（需启动后端）。
* **`test_optimization_workflow.py`**: 优化流程集成测试（直接调用服务类）。
* **`test_ml_service_internal.py`**: 机器学习服务内部逻辑测试。
* **`test_optimization_service_internal.py`**: 优化求解器服务内部逻辑测试。
* **`test_auth.py`**: 认证模块单元测试。
* **`test_mlops.py`**: MLOps 流程测试（Firebase 模型上传/下载）。

## 如何运行测试 (防御演示)

### 1. 准备工作

确保您在 `back` 目录下，并已激活虚拟环境：

```bash
cd /Users/achilles/Documents/code/data\ science/back
# 激活 python 环境 (根据实际情况)
```

### 2. 核心功能本地验证 (无需启动 Web 服务)

无需启动 Flask 服务器，直接运行以下脚本：

#### A. 演示能源优化核心算法 (MIP)

```bash
python3 tests/test_optimization_service_internal.py
```

> **预期输出**: 显示创建 EnergyOptimizer，模拟负载/电价数据，运行 Gurobi 优化，并输出充放电策略和节省金额。

#### B. 演示机器学习预测 (ML)

```bash
python3 tests/test_ml_service_internal.py
```

> **预期输出**: 实例化 EnergyPredictor，训练/加载模型，预测未来 24 小时负载，并展示预测结果列表。

#### C. 演示完整数据流 (预测 + 优化)

```bash
python3 tests/test_optimization_workflow.py
```

> **预期输出**: 串联预测和优化两个步骤。先预测负载，再基于预测结果进行电池调度。
