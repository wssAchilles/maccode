# ⚡ 智能能源管理与数据科学平台

> **Energy Management & Data Science Platform**
>
> 一个基于机器学习和数学优化的智能能源调度系统，采用全栈云原生架构，展示实力

[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://python.org)
[![Flutter](https://img.shields.io/badge/Flutter-3.10+-blue.svg)](https://flutter.dev)
[![GCP](https://img.shields.io/badge/Google%20Cloud-Platform-4285F4.svg)](https://cloud.google.com)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 📋 目录

- [项目概述](#-项目概述)
  - [项目亮点](#-项目亮点)
  - [业务价值](#-业务价值)
  - [模型性能快照](#-模型性能快照-model-performance)
- [核心功能与技术实现](#-核心功能与技术实现)
  - [能源优化调度引擎](#1-能源优化调度引擎-energy-optimization-engine-)
  - [负载时序预测微服务](#2-负载时序预测微服务-load-prediction-microservice-)
  - [可视化交互终端](#3-可视化交互终端-interactive-dashboard)
  - [云原生架构](#4-实时数据与云原生架构-cloud-native-infra-)
  - [可信 AI 与 MLOps](#5-可信-ai-与-mlops-模块-xai--mlops-)
  - [特征工程详解](#6-特征工程详解-feature-engineering-)
- [系统架构](#-系统架构)
- [技术栈详解](#-技术栈详解)
- [项目结构](#-项目结构)
- [快速开始](#-快速开始)
- [API 文档](#-api-文档)
- [部署指南](#-部署指南)
- [开发指南](#-开发指南)
- [测试](#-测试)
- [贡献指南](#-贡献指南)

---

## 🎯 项目概述

本项目是一个**智能能源管理平台**，旨在帮助用户优化电池储能系统的充放电调度，实现电费节省和能源效率最大化。

### 🌟 项目亮点

| 特性                     | 描述                                                 |
| ------------------------ | ---------------------------------------------------- |
| 🤖**智能模型选择** | 自动评估 RandomForest/LightGBM/XGBoost，选择最优模型 |
| 🔮**高精度预测**   | R²=97.16%, MAPE=1.40%，25 维特征工程                |
| 📊**数学优化**     | 基于 Gurobi 求解器的混合整数规划 (MIP) 优化          |
| 🌐**实时数据**     | 集成 CAISO 电网数据和 OpenWeatherMap 天气 API        |
| 📈**MLOps 监控**   | 在线性能评估，模型漂移检测，自动告警                 |
| ☁️**云原生架构** | 完全部署在 Google Cloud Platform                     |
| 🐳**容器化**       | 支持 Docker 部署，可移植到任何容器平台               |
| 📱**跨平台前端**   | Flutter Web 响应式设计，支持桌面和移动端             |

### 📈 业务价值

- **电费节省**: 通过智能调度，在低谷时段充电、高峰时段放电 (支持防逆流自用模式)
- **负载预测**: 基于历史数据和天气信息预测用电需求 (支持持久性基准校准)
- **数据分析**: 支持用户上传 CSV 数据进行统计分析
- **决策支持**: 可视化优化结果，支持 What-If 场景模拟 (真实温差仿真)

### 📊 模型性能快照 (Model Performance)

> 最新训练结果 (2024-12)

| 指标                  | 数值                   | 说明                   |
| --------------------- | ---------------------- | ---------------------- |
| 🏆**最佳模型**  | LightGBM_300           | 自动选择胜出           |
| 📈**R² Score** | **0.9716**       | 解释 97.16% 方差       |
| 📉**MAPE**      | **1.40%**        | 平均绝对百分比误差     |
| 🎯**Test MAE**  | 318.64 kW              | 测试集平均绝对误差     |
| 🔧**特征数量**  | 25                     | 12 基础 + 13 增强      |
| ⚡**提升幅度**  | 16.8%                  | 相比 RandomForest 基准 |
| ✅**验证方法**  | TimeSeriesSplit 5-Fold | 时间序列交叉验证       |

---

## 🚀 核心功能与技术实现

本章节详细拆解系统的核心模块，说明技术选型理由、代码实现位置及答辩时的关键技术亮点。

### 1. 能源优化调度引擎 (Energy Optimization Engine) ⚡

系统的大脑，负责制定最优的充放电策略。

- **核心技术栈**:

  - **Gurobi Optimizer**: 业界最强的数学规划求解器 (MIP Solver)。
  - **Python (gurobipy)**: 用于构建和运行优化模型。
- **项目中的实现**:

  - **代码位置**: `back/services/optimization_service.py` -> `EnergyOptimizer` 类。
  - **建模逻辑**: 将现实问题抽象为**混合整数规划 (MIP)** 问题，采用 **滚动时域优化 (Rolling Horizon Optimization)** 策略。
    - **滚动机制**: 每小时 ($t$) 基于最新的 24 小时预测数据 ($t \to t+24$) 重新求解优化问题，仅执行当前时刻 ($t$) 的调度指令，以此动态修正预测误差。
    - **决策变量**: `P_charge` (充), `P_discharge` (放) [连续变量]; `Is_charge`, `Is_discharge` [二进制变量]。
    - **约束构建**:
      1. **物理约束**: 能量守恒 $E_{t} = E_{t-1} + \eta P_{in} - P_{out}/\eta$。
      2. **互斥约束**: `Is_charge + Is_discharge <= 1` (防止同时充放电)。
      3. **安全约束**: $10\% \le SOC \le 90\%$ (保护电池寿命)。
      4. **防逆流约束**: `Grid_Power >= 0` (禁止向电网倒送电，确保自发自用)。
    - **目标函数**: $\min \sum (\text{Load} + P_{ch} - P_{dis}) \times \text{Price}$。
- **🎓 关键点 (Defense Points)**:

  - **Q: 为什么要用 Gurobi 而不是遗传算法?**
    - A: 遗传算法容易陷入局部最优 (Local Optima)，而 Gurobi 基于分支定界法 (Branch & Bound)，能保证找到**全局最优解** (Global Optimum)。对于涉及真金白银的经济调度，最优性至关重要。
  - **Q: 求解速度如何保证?**
    - A: 我们在 Docker 环境中配置了 Gurobi 的 Compute Server 模式，并在代码中设置了 `MIPGap=0.05`，在保证 95% 优度的前提下，将求解时间控制在 100ms 级别，满足实时响应需求。

### 2. 负载时序预测微服务 (Load Prediction Microservice) 🔮

系统的眼睛，洞察未来的能源需求。

- **核心技术栈**:

  - **Scikit-learn**: 机器学习建模与流水线。
  - **LightGBM / XGBoost**: 高性能梯度提升框架（可选）。
  - **Pandas**: 高效的时间序列特征工程。
  - **Joblib**: 模型的持久化与序列化。
  - **holidays**: 美国加州节假日判断（CAISO 区域）。
  - **Persistence Baseline**: 持久性预测基准 (用于 What-If 科学仿真)。
- **项目中的实现**:

  - **代码位置**: `back/services/ml_service.py` -> `EnergyPredictor` 类。
  - **自动模型选择 (AutoML)**:

    - 系统自动评估 **6 种模型配置**:
      | 模型         | 配置                  |
      | :----------- | :-------------------- |
      | RandomForest | n_estimators=100, 200 |
      | LightGBM     | n_estimators=100, 300 |
      | XGBoost      | n_estimators=100, 300 |
    - 使用 **TimeSeriesSplit 5 折交叉验证** 选择最优模型。
    - 当前最优: **LightGBM_300**，相比基准提升 **16.8%**。
  - **特征工程 (25 维特征)**:

    - **代码位置**: `back/services/data_processor.py` -> `EnergyDataProcessor` 类。
    - **基础特征 (12 维)**:

      | 序号 | 特征名            | 中文名          | 类型 | 详细说明                                                                    |
      | :--- | :---------------- | :-------------- | :--- | :-------------------------------------------------------------------------- |
      | 1    | Hour              | 小时            | 时间 | 一天中的小时数 (0-23)，反映负荷的日内周期性规律。白天商业用电高峰、夜间低谷 |
      | 2    | DayOfWeek         | 星期几          | 时间 | 一周中的第几天 (0-6，周一=0)，反映工作日/周末的用电差异                     |
      | 3    | Temperature       | 温度            | 气象 | 环境温度 (°F)，与空调/暖气负荷强相关。CAISO数据来自加州地区                |
      | 4    | Price             | 电价            | 经济 | 电力市场价格 ($/MWh)，反映供需关系，高价通常对应高负荷时段                  |
      | 5    | Lag_1h            | 1小时滞后       | 滞后 | 前1小时的负荷值 (kW)，捕捉短期惯性                                          |
      | 6    | Lag_24h           | 24小时滞后      | 滞后 | 前24小时（昨天同一时刻）的负荷值，捕捉日周期模式                            |
      | 7    | Lag_168h          | 168小时滞后     | 滞后 | 前168小时（上周同一时刻）的负荷值，捕捉周周期模式                           |
      | 8    | Rolling_Mean_6h   | 6小时滚动均值   | 统计 | 过去6小时负荷的移动平均，平滑短期波动                                       |
      | 9    | Rolling_Std_6h    | 6小时滚动标准差 | 统计 | 过去6小时负荷的波动程度，反映负荷稳定性                                     |
      | 10   | Rolling_Mean_24h  | 24小时滚动均值  | 统计 | 过去24小时负荷的移动平均，反映日平均水平                                    |
      | 11   | Temp_x_Hour       | 温度×小时      | 交互 | 温度与小时的乘积，捕捉"高温午后"等复合效应                                  |
      | 12   | Lag24_x_DayOfWeek | 24h滞后×星期   | 交互 | 滞后值与星期的乘积，捕捉"周一效应"等模式                                    |
    - **增强特征 (13 维)**:

      **A. 扩展时间特征 (6个)**

      | 序号 | 特征名     | 中文名     | 类型 | 详细说明                                             |
      | :--- | :--------- | :--------- | :--- | :--------------------------------------------------- |
      | 13   | Month      | 月份       | 时间 | 一年中的第几月 (1-12)，反映季节性用电变化            |
      | 14   | Season     | 季节       | 时间 | 四季编码：春=1, 夏=2, 秋=3, 冬=4，简化的季节模式     |
      | 15   | IsWeekend  | 是否周末   | 时间 | 二值标记 (0/1)，周末用电模式与工作日显著不同         |
      | 16   | IsHoliday  | 是否节假日 | 时间 | 二值标记 (0/1)，使用 holidays 库识别美国加州法定假日 |
      | 17   | DayOfMonth | 月中第几天 | 时间 | 一月中的第几天 (1-31)，可能与月末结算、发薪日等相关  |
      | 18   | WeekOfYear | 年中第几周 | 时间 | 一年中的第几周 (1-52)，更细粒度的年度周期特征        |

      **B. 增强交互特征 (3个)**

      | 序号 | 特征名            | 中文名        | 公式                      | 详细说明                            |
      | :--- | :---------------- | :------------ | :------------------------ | :---------------------------------- |
      | 19   | Temp_x_Season     | 温度×季节    | `Temperature × Season` | 捕捉"夏季高温"/"冬季低温"的复合效应 |
      | 20   | Lag24_x_IsWeekend | 24h滞后×周末 | `Lag_24h × IsWeekend`  | 区分周末/工作日的历史模式权重       |
      | 21   | Hour_x_IsHoliday  | 小时×节假日  | `Hour × IsHoliday`     | 捕捉节假日特有的时段用电模式        |

      **C. 周期编码特征 (4个)**


      > 使用正弦/余弦变换将周期性特征转为连续值，避免 "Hour=23 与 Hour=0 相邻但数值差异大" 的问题。
      >

      | 序号 | 特征名    | 中文名   | 公式                                  | 详细说明                               |
      | :--- | :-------- | :------- | :------------------------------------ | :------------------------------------- |
      | 22   | Month_Sin | 月份正弦 | $\sin(\frac{2\pi \cdot Month}{12})$ | 月份的正弦分量，让12月→1月平滑过渡    |
      | 23   | Month_Cos | 月份余弦 | $\cos(\frac{2\pi \cdot Month}{12})$ | 月份的余弦分量，与正弦共同编码完整周期 |
      | 24   | Hour_Sin  | 小时正弦 | $\sin(\frac{2\pi \cdot Hour}{24})$  | 小时的正弦分量，让23点→0点平滑过渡    |
      | 25   | Hour_Cos  | 小时余弦 | $\cos(\frac{2\pi \cdot Hour}{24})$  | 小时的余弦分量，与正弦共同编码日内周期 |
  - **模型性能指标**:

    | 指标      | 数值                | 说明               |
    | --------- | ------------------- | ------------------ |
    | R² Score | **0.9716**    | 解释 97.16% 的方差 |
    | MAPE      | **1.40%**     | 平均绝对百分比误差 |
    | Test MAE  | **318.64 kW** | 测试集平均绝对误差 |
    | 特征数量  | **25**        | 12 基础 + 13 增强  |
- **🎓 关键点**:

  - **Q: 为什么选择 LightGBM 而非深度学习?**
    - A: 相比于 LSTM/Transformer，梯度提升树在中小规模数据集（<10 万样本）上表现更稳健，训练速度快 100 倍以上，且**抗噪能力强**（能处理传感器异常值）。更重要的是具备**特征可解释性**，这对于工程应用排查问题非常有帮助。
  - **Q: 为什么要做自动模型选择?**
    - A: 不同数据集特性不同，没有"万能模型"。我们的 AutoML 机制会根据交叉验证结果**自动选择最优模型**，避免人工调参的主观性。LightGBM 在当前数据集上比 RandomForest 提升了 16.8%。
  - **Q: 如何防止过拟合?**
    - A: 采用了**时间序列交叉验证 (TimeSeriesSplit)**，严格按照时间轴划分训练集和测试集，杜绝了"未来数据泄露" (Data Leakage)。同时监控训练集与测试集的 MAE 差距。
  - **Q: 为什么要用周期编码 (Cyclic Encoding)?**
    - A: 小时和月份是循环变量，例如 23 点和 0 点应该"接近"。传统 One-Hot 编码无法表达这种关系，而 $\sin/\cos$ 编码将其映射到单位圆上，保持了时间的连续性。

### 3. 可视化交互终端 (Interactive Dashboard)

系统的门面，连接人与算法。

- **核心技术栈**:

  - **Flutter (Dart)**: Google 的跨平台 UI 框架。
  - **Provider**: 响应式状态管理。
  - **fl_chart**: 高性能图表渲染库。
- **项目中的实现**:

  - **代码位置**: `front/lib/screens/modeling_screen.dart`。
  - **状态管理**: 使用 `ChangeNotifier` 模式将 UI 与业务逻辑解耦。当 `OptimizationService` 返回结果时，通知图表组件重绘。
  - **性能优化**: 24小时 *60分钟* 多条曲线的数据量很大，我们在前端实现了**触控交互优化**，Tooltip 仅在长按时通过 `TouchCallback` 动态计算，保证了 60fps 的流畅度。
- **🎓 关键点**:

  - **Q: 为什么前端选择 Flutter?**
    - A: 我们的应用需要展示大量复杂的实时曲线。Flutter 拥有独立的 **Skia 渲染引擎**，不依赖 WebView，在绘制图表时性能远超传统的 React Native 或 H5 方案。

### 4. 实时数据与云原生架构 (Cloud Native Infra) ☁️

系统的骨架，支撑全链路运行。

- **核心技术栈**:

  - **Google App Engine (GAE)**: Serverless 计算平台。
  - **Docker**: 容器化封装。
  - **APScheduler**: 分布式任务调度。
- **项目中的实现**:

  - **代码位置**: `back/main.py` (Flask 入口), `Dockerfile`, `app.yaml`。
  - **实时流**:
    1. `scheduler.py` 每小时触发一次。
    2. 调用 `ExternalDataService` 从 CAISO/OpenWeatherMap 拉取最新数据。
    3. 数据存入 **Firestore** 并触发预测任务。
  - **云端部署**: 使用多阶段构建 (Multi-stage Build) 将 Docker 镜像体积压缩至 150MB，实现 GAE 的秒级扩容。
- **🎓 答辩关键点**:

  - **Q: 系统的高可用性 (High Availability) 如何保证?**
    - A: 基于 Serverless 架构，Google App Engine 会根据流量自动扩缩容实例。同时，我们的 Gurobi 许可证配置采用了**动态注入**机制 (Environment Secrets)，确保了在任何云实例上都能无缝启动求解服务。

### 5. 可信 AI 与 MLOps 模块 (XAI & MLOps) 🧠

系统的审计官，确保决策透明、模型可靠。

- **核心技术栈**:

  - **SHAP**: 博弈论解释模型。
  - **Scikit-learn Metrics**: R², MAPE, MAE 等评估指标。
  - **Firebase Storage**: 模型版本化存储。
- **项目中的实现**:

  - **可解释性 (XAI)**:

    - **代码位置**: `front/lib/widgets/analysis/feature_importance_chart.dart`
    - 前端展示"特征贡献度"水平条形图，支持**展开/折叠** 25 个特征。
    - 直观告诉用户："为什么预测负载高？因为 `Rolling_Mean_6h` 贡献了 11.2%"。
    - **Top 3 特征摘要**：快速定位最重要的影响因素。
  - **模型性能监控 (MLOps)**:

    - **代码位置**: `back/services/ml_service.py` -> `evaluate_recent_performance()`
    - **在线评估**: 每次优化请求时，自动计算最近 24 小时的 R², MAPE, MAE。
    - **前端展示**: R² 圆形进度条 (绿色 >80%), MAPE 线性进度条 (<10% 为绿色)
    - **模型漂移检测**: 若 MAPE 持续上升，提示重新训练。
  - **模型版本化**: Firebase Storage 存储 `models/model_metadata.json`，记录训练历史。
  - **自动模型选择展示**: 前端显示胜出模型、性能提升、验证方法等信息。
- **🎓 关键点**:

  - **Q: 如何判断模型需要重新训练?**
    - A: 在线 MAPE 监控，当 MAPE 超过训练时的 2 倍，触发告警提示 Concept Drift。
  - **Q: 为什么要展示特征重要性?**
    - A: 可解释性是"可信 AI"的核心，有助于发现数据问题。

### 6. 特征工程详解 (Feature Engineering) 🔬

将原始数据转化为模型可学习的信号。

- **代码位置**: `back/services/data_processor.py` -> `EnergyDataProcessor` 类
- **特征分类**:

  | 类别               | 特征                            | 数学表达 / 说明                                          |
  | ------------------ | ------------------------------- | -------------------------------------------------------- |
  | **滞后特征** | Lag_1h, Lag_24h, Lag_168h       | $X_{t-1}, X_{t-24}, X_{t-168}$                         |
  | **滚动统计** | Rolling_Mean_6h, Rolling_Std_6h | $\frac{1}{6}\sum_{i=1}^{6}X_{t-i}$, $\sigma_{6h}$    |
  | **周期编码** | Hour_Sin, Hour_Cos              | $\sin(\frac{2\pi h}{24})$, $\cos(\frac{2\pi h}{24})$ |
  | **日历特征** | IsWeekend, IsHoliday            | 二值编码 (0/1)                                           |
  | **交叉特征** | Temp_x_Season, Hour_x_IsHoliday | 非线性交互项                                             |
- **特征重要性 Top 5** (基于 LightGBM):

  | 排名 | 特征            | 重要性 | 解释                 |
  | ---- | --------------- | ------ | -------------------- |
  | 1    | Lag_1h          | 1000   | 上一小时负载（惯性） |
  | 2    | Rolling_Mean_6h | 962    | 近期趋势             |
  | 3    | Lag_168h        | 696    | 上周同时刻（周期性） |
  | 4    | Lag_24h         | 690    | 昨日同时刻           |
  | 5    | Rolling_Std_6h  | 686    | 负载波动性           |
- **🎓 关键点**:

  - **Q: 为什么滞后特征比温度更重要?**
    - A: 能源负载具有强**自相关性**。当前负载主要由近期负载决定，而温度是**调节因素**。这符合工程直觉：用户用电行为有惯性。
  - **Q: 周期编码的好处?**
    - A: 将离散的时间 (0-23h) 映射到连续空间，使 23:00 和 00:00 "接近"，避免 One-Hot 编码的维度爆炸。

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                          用户层 (User Layer)                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │              Flutter Web Application                         │   │
│   │  ┌─────────┐ ┌─────────────┐ ┌──────────┐ ┌─────────────┐   │   │
│   │  │ 登录页面 │ │ 数据分析页面 │ │ 优化页面 │ │ 历史记录页面 │   │   │
│   │  └─────────┘ └─────────────┘ └──────────┘ └─────────────┘   │   │
│   └─────────────────────────────────────────────────────────────┘   │
│                              │                                      │
│                    Firebase Auth (ID Token)                         │
│                              ▼                                      │
├─────────────────────────────────────────────────────────────────────┤
│                          API 网关层                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │              Flask REST API (Google App Engine)              │   │
│   │  ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐ │   │
│   │  │ /auth   │ │ /data    │ │/analysis │ │ /optimization    │ │   │
│   │  └─────────┘ └──────────┘ └──────────┘ └──────────────────┘ │   │
│   └─────────────────────────────────────────────────────────────┘   │
│                              │                                      │
├─────────────────────────────────────────────────────────────────────┤
│                          服务层 (Service Layer)                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   ┌───────────────┐ ┌───────────────┐ ┌───────────────────────┐     │
│   │ AnalysisService│ │  MLService   │ │ OptimizationService  │     │
│   │  (Pandas/SciPy)│ │(Scikit-learn)│ │     (Gurobi MIP)     │     │
│   └───────────────┘ └───────────────┘ └───────────────────────┘     │
│                                                                     │
│   ┌───────────────┐ ┌───────────────┐ ┌───────────────────────┐     │
│   │ StorageService│ │FirebaseService│ │ExternalDataService   │     │
│   │     (GCS)     │ │  (Firestore)  │ │ (CAISO/Weather API)  │     │
│   └───────────────┘ └───────────────┘ └───────────────────────┘     │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│                          数据层 (Data Layer)                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   ┌─────────────────┐  ┌──────────────┐  ┌────────────────────┐     │
│   │ Cloud Storage   │  │  Firestore   │  │  External APIs     │     │
│   │ (文件/模型存储)  │  │ (用户数据/历史)│  │ (CAISO/Weather)   │     │
│   └─────────────────┘  └──────────────┘  └────────────────────┘     │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ 技术栈详解

### 后端技术栈

| 类别                  | 技术           | 版本    | 用途                  |
| --------------------- | -------------- | ------- | --------------------- |
| **Web 框架**    | Flask          | 3.0.0   | RESTful API 服务      |
| **WSGI 服务器** | Gunicorn       | 21.2.0  | 生产环境部署          |
| **跨域处理**    | Flask-CORS     | 4.0.0   | CORS 支持             |
| **数据处理**    | Pandas         | 1.5.3+  | 数据分析与处理        |
| **数值计算**    | NumPy          | 1.26.2+ | 数值计算              |
| **科学计算**    | SciPy          | 1.11.4+ | 统计检验              |
| **机器学习**    | Scikit-learn   | 1.3.2   | 基础 ML 框架          |
| **梯度提升**    | LightGBM       | 4.0.0+  | 高性能树模型 (AutoML) |
| **梯度提升**    | XGBoost        | 2.0.0+  | 高性能树模型 (AutoML) |
| **节假日处理**  | holidays       | 0.40+   | 美国加州节假日        |
| **可解释性**    | SHAP           | 0.44.1  | 模型预测解释          |
| **优化求解**    | Gurobi         | 10.0.3  | 混合整数规划 (MIP)    |
| **实时数据**    | GridStatus     | 0.26.0+ | CAISO 电网数据        |
| **任务调度**    | APScheduler    | 3.10.4  | 分布式定时任务        |
| **云服务**      | Firebase Admin | 6.5.0   | 认证与存储            |

### 前端技术栈

| 类别               | 技术              | 版本     | 用途       |
| ------------------ | ----------------- | -------- | ---------- |
| **框架**     | Flutter           | ≥3.10.0 | 跨平台 UI  |
| **认证**     | Firebase Auth     | 6.1.2    | 用户认证   |
| **HTTP**     | http              | 1.1.0    | API 调用   |
| **文件选择** | file_picker       | 8.0.0    | 文件上传   |
| **图表**     | fl_chart          | 1.1.1    | 数据可视化 |
| **进度指示** | percent_indicator | 4.2.3    | 进度展示   |
| **国际化**   | intl              | 0.20.2   | 日期格式化 |

### 云平台与基础设施

| 服务                              | 用途                             |
| --------------------------------- | -------------------------------- |
| **Google App Engine**       | 后端 API 托管 (Serverless)       |
| **Firebase Hosting**        | 前端静态资源托管                 |
| **Firebase Authentication** | 用户身份认证 (Google/Email)      |
| **Cloud Storage**           | 文件存储 (CSV/模型文件)          |
| **Cloud Firestore**         | NoSQL 数据库 (用户数据/历史记录) |
| **Cloud Scheduler**         | 定时任务触发 (GAE Cron)          |

### DevOps 工具链

| 工具                     | 用途              |
| ------------------------ | ----------------- |
| **Docker**         | 容器化部署        |
| **Docker Compose** | 本地开发环境编排  |
| **pytest**         | Python 单元测试   |
| **gcloud CLI**     | GCP 部署管理      |
| **Firebase CLI**   | Firebase 部署管理 |

---

## 📁 项目结构

```
data-science/
├── 📂 back/                          # 后端服务 (Python/Flask)
│   ├── 📂 api/                       # API 路由层 (Blueprints)
│   │   ├── auth.py                   # 认证 API (Firebase Verify)
│   │   ├── data.py                   # 数据管理 API (Upload/List)
│   │   ├── analysis.py               # 数据分析 API (Pandas Profiling)
│   │   ├── optimization.py           # 优化调度 API (Trigger Gurobi)
│   │   ├── history.py                # 历史记录 API (Read Firestore)
│   │   └── ml.py                     # 机器学习 API (Train/Predict)
│   │
│   ├── 📂 services/                  # 核心业务逻辑层 (Domain Services)
│   │   ├── optimization_service.py   # ⚡ 能源优化引擎 (Gurobi MIP核心)
│   │   ├── ml_service.py             # 🔮 负载预测服务 (Scikit-learn/LGBM)
│   │   ├── external_data_service.py  # 🌐 外部数据服务 (CAISO/OpenWeather)
│   │   ├── analysis_service.py       # 📊 数据分析服务 (Stats/Correlation)
│   │   ├── data_processor.py         # 🔧 特征工程处理 (Feature Eng.)
│   │   ├── firebase_service.py       # 🔥 Firebase 认证集成
│   │   ├── storage_service.py        # ☁️ GCS 文件存储操作
│   │   └── history_service.py        # 📜 历史记录持久化
│   │
│   ├── 📂 middleware/                # Flask 中间件
│   │   ├── logging.py                # 请求日志与监控
│   │   └── rate_limit.py             # API 限流保护
│   │
│   ├── 📂 models/                    # 数据模型定义
│   │   └── schemas.py                # Pydantic/Marshmallow 模式
│   │
│   ├── 📂 tests/                     # 自动化测试套件
│   │   ├── conftest.py               # Pytest Fixtures
│   │   ├── test_auth.py              # 认证模块测试
│   │   └── services/                 # 服务单元测试 (Mocked)
│   │
│   ├── main.py                       # Flask 应用工厂入口
│   ├── config.py                     # 全局配置管理 (Env Vars)
│   ├── scheduler.py                  # APScheduler 定时任务 (Cron)
│   ├── requirements.txt              # 后端依赖列表
│   ├── app.yaml                      # Google App Engine 部署配置
│   └── Dockerfile                    # 生产环境容器构建文件
│
├── 📂 front/                         # 前端应用 (Flutter Web)
│   ├── 📂 lib/
│   │   ├── 📂 screens/               # 页面级组件
│   │   │   ├── modeling_screen.dart          # ⚡ 核心优化工作台
│   │   │   ├── data_analysis_screen.dart     # 📊 数据分析仪表盘
│   │   │   ├── analysis_detail_screen.dart   # 🔍 深度分析详情
│   │   │   └── history_screen.dart           # 📜 历史记录列表
│   │   │
│   │   ├── 📂 services/              # 前端服务层
│   │   │   ├── api_service.dart      # HTTP 请求封装
│   │   │   └── auth_service.dart     # Firebase Auth 封装
│   │   │
│   │   ├── 📂 models/                # Dart 数据模型
│   │   ├── 📂 widgets/               # 可复用 UI 组件
│   │   │   ├── 📂 analysis/          # 分析图表组件 (fl_chart)
│   │   │   └── ...
│   │   └── main.dart                 # Flutter 应用入口
│   │
│   └── pubspec.yaml                  # Dart 依赖配置
│
├── 📂 scripts/                       # DevOps 与运维脚本
│   ├── deploy_backend.sh             # 后端一键部署脚本
│   ├── test_api.py                   # API 端到端集成测试
│   └── sync_data.py                  # 手动数据同步工具
│
└── docker-compose.yml                # 本地全栈开发环境编排
```

---

## 🚀 快速开始

### 环境要求

| 工具       | 最低版本 | 说明              |
| ---------- | -------- | ----------------- |
| Python     | 3.11+    | 后端运行时        |
| Flutter    | 3.10+    | 前端开发          |
| Docker     | 20.10+   | 容器化部署 (可选) |
| Node.js    | 18+      | Firebase CLI      |
| gcloud CLI | 最新     | GCP 部署          |

### 方式一：本地开发

#### 1. 克隆项目

```bash
git clone https://github.com/WssAchilles/maccode.git
cd "data science"
```

#### 2. 后端设置

```bash
# 进入后端目录
cd back

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入你的配置

# 启动开发服务器
python main.py
```

#### 3. 前端设置

```bash
# 进入前端目录
cd front

# 获取依赖
flutter pub get

# 启动开发服务器
flutter run -d chrome
```

### 方式二：Docker 部署

```bash
# 配置环境变量
cp back/.env.example back/.env
# 编辑 back/.env 文件

# 构建并启动所有服务
docker compose up --build

# 后台运行
docker compose up -d

# 查看日志
docker compose logs -f

# 访问应用
# 前端: http://localhost:3000 (或 http://localhost:80 取决于 nginx 配置)
# 后端: http://localhost:8080
```

### 方式三：云端部署

详见 [部署指南](#-部署指南) 章节。

---

## 📚 API 文档

### 基础信息

| 项目     | 值                                              |
| -------- | ----------------------------------------------- |
| 基础 URL | `https://data-science-44398.an.r.appspot.com` |
| API 版本 | v1                                              |
| 认证方式 | Firebase ID Token (Bearer)                      |
| 内容类型 | application/json                                |

### 认证相关

#### 验证 Token

```http
POST /api/auth/verify
Authorization: Bearer <Firebase ID Token>
```

**响应示例:**

```json
{
  "success": true,
  "user": {
    "uid": "abc123",
    "email": "user@example.com",
    "email_verified": true
  }
}
```

#### 获取用户资料

```http
GET /api/auth/profile
Authorization: Bearer <Firebase ID Token>
```

### 数据管理

#### 获取上传 URL

```http
POST /api/data/upload-url
Authorization: Bearer <Firebase ID Token>
Content-Type: application/json

{
  "fileName": "data.csv",
  "contentType": "text/csv"
}
```

**响应示例:**

```json
{
  "success": true,
  "upload_url": "https://storage.googleapis.com/...",
  "storage_path": "uploads/uid/data.csv"
}
```

#### 列出用户文件

```http
GET /api/data/list
Authorization: Bearer <Firebase ID Token>
```

### 数据分析

#### 分析 CSV 文件

```http
POST /api/analysis/analyze-csv
Authorization: Bearer <Firebase ID Token>
Content-Type: application/json

{
  "storage_path": "uploads/uid/data.csv",
  "filename": "data.csv"
}
```

**响应示例:**

```json
{
  "success": true,
  "analysis_result": {
    "basic_info": {
      "rows": 8760,
      "columns": 10,
      "column_names": ["Timestamp", "Load", "Temperature", ...],
      "column_types": {"Timestamp": "datetime64", "Load": "float64", ...}
    },
    "descriptive_stats": {
      "statistics": {
        "Load": {"mean": 198.42, "std": 56.78, "min": 113.05, "max": 380.32, ...}
      }
    },
    "quality_analysis": {
      "missing_percentage": 0.5,
      "duplicate_rows": 0,
      "outliers": {...}
    },
    "correlations": {
      "pearson": {...},
      "spearman": {...}
    },
    "statistical_tests": {
      "normality": {...},
      "stationarity": {...}
    }
  }
}
```

### 能源优化

#### 执行优化调度

```http
POST /api/optimization/run
Authorization: Bearer <Firebase ID Token>
Content-Type: application/json

```json
{
  "initial_soc": 0.5,
  "target_date": "2024-11-24",
  "battery_capacity": 13.5,
  "battery_power": 5.0,
  "temperature_forecast": [24.0, 23.5, ...]
}
```

**响应示例:**

```json
{
  "success": true,
  "optimization": {
    "status": "Optimal",
    "chart_data": [
      {
        "hour": 0,
        "datetime": "2024-11-24T00:00:00",
        "load": 20.54,
        "price": 0.3,
        "battery_action": 2.0,
        "charge_power": 2.0,
        "discharge_power": 0.0,
        "soc": 0.53,
        "grid_power": 22.54
      }
    ],
    "summary": {
      "total_cost_without_battery": 125.60,
      "total_cost_with_battery": 110.89,
      "savings": 14.71,
      "savings_percent": 11.7,
      "total_load": 476.2,
      "total_charged": 15.2,
      "total_discharged": 14.1,
      "peak_load": 38.03,
      "min_load": 11.30
    },
    "strategy": {
      "charging_hours": [0, 1, 2, 3, 4, 5],
      "discharging_hours": [18, 19, 20, 21],
      "charging_count": 6,
      "discharging_count": 4
    }
  },
  "prediction": {
    "target_date": "2024-11-24",
    "avg_load": 19.84,
    "peak_load": 38.03,
    "min_load": 11.30
  },
    "max_power": 5.0,
    "efficiency": 0.95
  },
  "model_explainability": {
    "feature_contributions": {
      "Temperature": 15.2,
      "Hour": -5.1,
      "DayOfWeek": 2.3
    },
    "interpretation": "Temperature 是影响最大的因素，它使得预测负载增加了 15.2 kW。"
  },
  "metrics": {
    "status": "success",
    "mape": 12.5,
    "r2": 0.85,
    "samples": 24,
    "last_data_time": "2024-11-24 12:00:00"
  }
}
```

### 历史记录

#### 获取分析历史

```http
GET /api/history/analyses?limit=10
Authorization: Bearer <Firebase ID Token>
```

#### 获取优化历史

```http
GET /api/history/optimizations?limit=10
Authorization: Bearer <Firebase ID Token>
```

### 健康检查

```http
GET /api/health
```

**响应:**

```json
{
  "status": "ok",
  "timestamp": "2024-11-24T12:00:00Z"
}
```

---

## 🚢 部署指南

### Google Cloud Platform 部署

#### 前置条件

1. 创建 GCP 项目
2. 启用以下 API:

   - App Engine Admin API
   - Cloud Storage API
   - Cloud Firestore API
   - Cloud Scheduler API
3. 安装并配置 gcloud CLI:

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

#### 部署后端到 App Engine

```bash
cd back

# 部署应用
gcloud app deploy app.yaml

# 部署定时任务 (可选)
gcloud app deploy cron.yaml
```

**`app.yaml` 配置说明:**

```yaml
runtime: python311
entrypoint: gunicorn -b :$PORT --timeout 300 --workers 1 main:app

instance_class: F4  # 高性能实例

automatic_scaling:
  min_instances: 0    # 无流量时自动缩容到 0
  max_instances: 1    # 限制最大实例数控制成本

env_variables:
  GCP_PROJECT_ID: "your-project-id"
  STORAGE_BUCKET_NAME: "your-bucket.appspot.com"
  GRB_LICENSEID: "your-license-id"
  GRB_WLSACCESSID: "your-access-id"
  GRB_WLSSECRET: "your-secret"
```

#### 部署前端到 Firebase Hosting

```bash
cd front

# 构建 Web 版本
flutter build web --release

# 部署到 Firebase Hosting
firebase deploy --only hosting
```

### Docker 部署

详见 [README_DOCKER.md](README_DOCKER.md)。

#### 部署到 Cloud Run

```bash
# 构建镜像
cd back
gcloud builds submit --tag gcr.io/YOUR_PROJECT/backend

# 部署到 Cloud Run
gcloud run deploy backend \
  --image gcr.io/YOUR_PROJECT/backend \
  --platform managed \
  --region asia-northeast1 \
  --allow-unauthenticated \
  --set-env-vars "GRB_LICENSEID=xxx,GRB_WLSACCESSID=xxx,GRB_WLSSECRET=xxx"
```

---

## 👨‍💻 开发指南

### 代码规范

#### Python (后端)

- 遵循 [PEP 8](https://pep8.org/) 代码规范
- 使用 Type Hints 进行类型注解
- 文档字符串使用 Google Style

```python
def analyze_data(df: pd.DataFrame, filename: str) -> Dict[str, Any]:
    """
    分析 DataFrame 数据。
  
    Args:
        df: 输入的 Pandas DataFrame
        filename: 文件名
  
    Returns:
        包含分析结果的字典
  
    Raises:
        ValidationError: 数据验证失败时
    """
    pass
```

#### Dart (前端)

- 遵循 [Dart 风格指南](https://dart.dev/guides/language/effective-dart/style)
- 使用 `flutter_lints` 进行代码检查
- 组件命名使用 PascalCase

```dart
/// 能源优化仪表盘
/// 
/// 展示优化结果和交互式参数配置
class ModelingScreen extends StatefulWidget {
  const ModelingScreen({super.key});
  
  @override
  State<ModelingScreen> createState() => _ModelingScreenState();
}
```

### 分支策略

| 分支          | 用途         |
| ------------- | ------------ |
| `main`      | 生产环境代码 |
| `develop`   | 开发环境代码 |
| `feature/*` | 功能开发分支 |
| `hotfix/*`  | 紧急修复分支 |

### 提交规范

使用 [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: 添加能源优化功能
fix: 修复 CSV 解析错误
docs: 更新 API 文档
refactor: 重构分析服务
test: 添加单元测试
chore: 更新依赖版本
```

### 环境变量

#### 后端环境变量

| 变量名                  | 必填 | 说明                              |
| ----------------------- | ---- | --------------------------------- |
| `GCP_PROJECT_ID`      | ✅   | GCP 项目 ID                       |
| `STORAGE_BUCKET_NAME` | ✅   | Cloud Storage 存储桶名            |
| `GRB_LICENSEID`       | ✅   | Gurobi 许可证 ID                  |
| `GRB_WLSACCESSID`     | ✅   | Gurobi WLS Access ID              |
| `GRB_WLSSECRET`       | ✅   | Gurobi WLS Secret                 |
| `OPENWEATHER_API_KEY` | ⬜   | OpenWeatherMap API Key            |
| `FLASK_ENV`           | ⬜   | 环境模式 (development/production) |
| `SECRET_KEY`          | ⬜   | Flask Secret Key                  |

#### 前端配置

前端配置位于 `front/lib/config/constants.dart`:

```dart
class AppConstants {
  static const String apiBaseUrl = 
    'https://data-science-44398.an.r.appspot.com';
  static const double defaultInitialSoc = 0.5;
  // ...
}
```

---

## 🧪 测试

### 环境准备

运行测试前需设置 GCP 凭证环境变量（用于需要 Firebase 连接的集成测试）:

```bash
export GOOGLE_APPLICATION_CREDENTIALS="/路径/到/service-account-key.json"
```

### 后端测试

```bash
cd back

# 运行所有测试
pytest tests/ -v

# 运行带覆盖率报告的测试
pytest tests/ --cov=services --cov-report=term-missing

# 只运行快速单元测试 (跳过慢速模型训练)
pytest tests/ -m "not slow" -v
```

### 测试结构

```
back/tests/
├── conftest.py                       # pytest 配置和公共 fixtures
├── test_auth.py                      # 认证 API 测试 (5 用例)
├── test_mlops.py                     # MLOps 集成测试 (2 用例)
├── api/                              # API 层测试
│   └── __init__.py
└── services/                         # 服务层测试
    ├── __init__.py
    ├── test_optimization_service.py  # 优化服务测试 (10 用例)
    ├── test_ml_service.py            # ML 服务测试 (11 用例)
    ├── test_data_processor.py        # 数据处理器测试
    └── test_analysis_enhanced.py     # 分析服务测试
```

### 测试标记

| 标记                         | 说明                      |
| ---------------------------- | ------------------------- |
| `@pytest.mark.unit`        | 单元测试（无外部依赖）    |
| `@pytest.mark.integration` | 集成测试（需要 GCP 凭证） |
| `@pytest.mark.slow`        | 慢速测试（如模型训练）    |

### 手动测试脚本

以下脚本位于 `scripts/` 目录，用于手动端到端测试:

```bash
# API 端到端集成测试 (验证真实服务器响应)
python scripts/test_api.py

# 优化流程直接测试 (验证 Gurobi 求解器逻辑)
python scripts/test_optimization_direct.py

# 数据同步 (手动触发 CAISO/Weather 拉取)
python scripts/sync_data.py
```

### 前端测试

```bash
cd front

# 运行单元测试
flutter test

# 运行集成测试
flutter test integration_test/
```

---

## 🔧 常见问题

### Q1: Gurobi 许可证错误?

确保已正确配置 WLS 环境变量:

```bash
export GRB_LICENSEID=your-license-id
export GRB_WLSACCESSID=your-access-id
export GRB_WLSSECRET=your-secret
```

### Q2: Firebase 认证失败?

1. 检查 Firebase 项目配置
2. 确保已启用 Google 登录提供商
3. 检查 OAuth 客户端 ID 配置

### Q3: CORS 错误?

检查后端 `config.py` 中的 `CORS_ORIGINS` 是否包含前端域名。

### Q4: 数据分析超时?

- 大文件 (>50MB) 可能需要更长时间
- GAE 默认超时 60 秒，已配置为 300 秒
- 考虑分割大文件或使用异步处理

---

## 🤝 贡献指南

欢迎贡献代码！请遵循以下步骤:

1. Fork 本仓库
2. 创建功能分支: `git checkout -b feature/AmazingFeature`
3. 提交更改: `git commit -m 'feat: Add AmazingFeature'`
4. 推送分支: `git push origin feature/AmazingFeature`
5. 提交 Pull Request

### 开发环境设置

```bash
# 安装开发依赖
cd back
pip install -r requirements.txt
pip install -r requirements-dev.txt  # 如果有的话

# 安装 pre-commit hooks (可选)
pre-commit install
```

---

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件。

---

## 📮 联系方式

- **项目维护者**: Achilles
- **GitHub**: [WssAchilles](https://github.com/WssAchilles)
- **项目地址**: [maccode](https://github.com/WssAchilles/maccode)

---

## 🙏 致谢

- [Google Cloud Platform](https://cloud.google.com/) - 云基础设施
- [Firebase](https://firebase.google.com/) - 认证与托管
- [Gurobi](https://www.gurobi.com/) - 优化求解器
- [Flutter](https://flutter.dev/) - 跨平台 UI 框架
- [CAISO](http://www.caiso.com/) - 电网数据
- [OpenWeatherMap](https://openweathermap.org/) - 天气数据

---

<p align="center">
  Made with ❤️ for Data Science
</p>
